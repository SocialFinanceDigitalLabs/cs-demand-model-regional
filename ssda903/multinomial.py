from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional

import numpy as np
import pandas as pd
from demand_model.base import BaseModelPredictor
from demand_model.multinomial.utils import (
    build_transition_rates_matrix,
    fill_missing_states,
    populate_same_state_transition,
)

try:
    import tqdm
except ImportError:
    tqdm = None


@dataclass
class Prediction:
    population: pd.DataFrame
    variance: pd.DataFrame
    transition_rates: pd.Series
    entry_rates: pd.Series


@dataclass
class NextPrediction:
    population: np.ndarray
    variance: np.ndarray


def combine_rates(original_rate: pd.Series, rate_adjustment: pd.DataFrame) -> pd.Series:
    """
    Combines original_rate series and rate_adjustment DataFrame, which has both 'multiply_value' and 'add_value' columns.
    - Multiplies original_rate with 'multiply_value' where provided.
    - Adds 'add_value' to original_rate where provided.
    - Ensures the result of addition is not less than 0.
    - Excludes cases where original_rate is missing.
    """
    # Ensure rate_adjustment has the required columns
    if not {"multiply_value", "add_value"}.issubset(rate_adjustment.columns):
        raise ValueError(
            "Adjusted rate dataframe must have 'multiply_value' and 'add_value' columns."
        )

    # Align original_rate and rate_adjustment DataFrame with a left join to retain all indices from original_rate
    original_rate, rate_adjustment = original_rate.align(rate_adjustment, join="left")

    # Fill missing values: multiply_value with 1 (neutral for multiplication), add_value with 0 (neutral for addition)
    rate_adjustment["multiply_value"].fillna(1, inplace=True)
    rate_adjustment["add_value"].fillna(0, inplace=True)

    # Create a mask to identify where original_rate is not missing
    mask = ~original_rate.isna()

    # Multiply original_rate by 'multiply_value' where it exists
    multiply_result = original_rate * rate_adjustment["multiply_value"]

    # Add 'add_value' to original_rate where it exists, ensuring the result is not less than 0
    add_result = original_rate + rate_adjustment["add_value"]
    add_result = add_result.clip(lower=0)  # Ensure no negative values

    # Choose between the multiplication and the addition result
    # If 'multiply_value' is not 1, use multiplication result; otherwise, use add result
    final_result = multiply_result.where(
        rate_adjustment["multiply_value"] != 1, add_result
    )

    # Apply the mask to exclude undesired cases (where original_rate is missing)
    final_result = final_result[mask]
    final_result.index.names = ["from", "to"]

    return final_result


class MultinomialPredictor(BaseModelPredictor):
    def __init__(
        self,
        population: pd.Series,
        transition_rates: pd.Series,
        transition_numbers: Optional[pd.Series] = None,
        start_date: date = date.today(),
        rate_adjustment: Optional[pd.DataFrame] = None,
        number_adjustment: Optional[pd.DataFrame] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)

        # initialize rates
        transition_rates.index.names = ["from", "to"]
        if rate_adjustment is not None:
            if isinstance(rate_adjustment, pd.DataFrame):
                rate_adjustment = [rate_adjustment]
            for adjustment in rate_adjustment:
                adjustment = adjustment.copy()
                adjustment.index.names = ["from", "to"]
                transition_rates = combine_rates(transition_rates, adjustment)

        self._transition_rates = populate_same_state_transition(transition_rates)
        self._matrix = build_transition_rates_matrix(self._transition_rates)

        # initialize transition numbers
        if transition_numbers is None:
            self._transition_numbers = pd.Series(0, index=self._matrix.index)
        else:
            transition_numbers.index.names = ["from", "to"]

            if number_adjustment is not None:
                if isinstance(number_adjustment, pd.DataFrame):
                    number_adjustment = [number_adjustment]
                for adjustment in number_adjustment:
                    adjustment = adjustment.copy()
                    new_index = pd.MultiIndex.from_product(
                        [[()], adjustment.index], names=["from", "to"]
                    )
                    adjustment.index = new_index
                    transition_numbers = combine_rates(transition_numbers, adjustment)

            transition_numbers.index = transition_numbers.index.get_level_values("to")
            self._transition_numbers = fill_missing_states(
                transition_numbers, self._matrix.index
            )

        # initialize population
        self._initial_population = fill_missing_states(population, self._matrix.index)
        self._start_date = start_date

    @property
    def matrix(self) -> pd.DataFrame:
        return self._matrix.copy()

    @property
    def transition_rates(self) -> pd.Series:
        return self._transition_rates.copy()

    @property
    def transition_numbers(self) -> pd.Series:
        return self._transition_numbers.copy()

    @property
    def initial_population(self) -> pd.Series:
        return self._initial_population.copy()

    @property
    def date(self) -> date:
        return self._start_date

    def next(self, population: np.ndarray, step_days: int = 1) -> NextPrediction:
        assert step_days > 0, "'step_days' must be greater than 0"
        for _ in range(step_days):
            variance = (
                np.dot(
                    np.multiply(self.matrix.values, 1 - self.matrix.values), population
                )
                + self.transition_numbers.values
            )
            population = (
                np.dot(self.matrix.values, population) + self.transition_numbers.values
            )
        return NextPrediction(population, variance)

    def predict(self, steps: int = 1, step_days: int = 1, progress=False) -> Prediction:
        predictor = self

        if progress and tqdm:
            iterator = tqdm.trange(steps)
            set_description = iterator.set_description
        else:
            iterator = range(steps)
            set_description = lambda x: None

        predictions = []
        variances = []
        index = []
        population = self.initial_population.values
        for i in iterator:
            prediction = predictor.next(population, step_days=step_days)
            population = prediction.population
            predictions.append(population)
            variances.append(prediction.variance)

            date = self.date + timedelta(days=(i + 1) * step_days)
            index.append(date)
            set_description(f"{date:%Y-%m}")

        df_entry_rates = self.transition_numbers

        df_transition_rates = self._transition_rates

        df_predictions = pd.DataFrame(
            predictions,
            columns=self.initial_population.index,
            index=index,
        )
        df_variances = pd.DataFrame(
            variances,
            columns=self.initial_population.index,
            index=index,
        )
        return Prediction(
            df_predictions, df_variances, df_transition_rates, df_entry_rates
        )
