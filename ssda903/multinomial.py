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


def normalize_rates(group, is_adjusted):
    """
    Normalizes rates to ensure that the sum of rates for each 'from' state is 1.
    Ensures that rate adjustments are prioritized over the original rates.
    """
    total = group.sum()
    if total > 1:
        # Separate adjusted and original rates
        adjusted = group[is_adjusted.loc[group.index]]
        original = group[~is_adjusted.loc[group.index]]

        adjusted_sum = adjusted.sum()
        if adjusted_sum >= 1:
            # Scale down adjusted rates to sum to 1, set original rates to 0
            scaling_factor = 1 / adjusted_sum
            adjusted = adjusted * scaling_factor
            original[:] = 0
        else:
            # Scale down adjusted rates and distribute remaining capacity to original rates
            adjusted = adjusted
            remaining_capacity = 1 - adjusted.sum()
            if not original.empty:
                original = original * (remaining_capacity / original.sum())
        # Combine adjusted and original back together
        group = pd.concat([adjusted, original]).sort_index()
    return group


def combine_rates(
    original_rate: pd.Series, rate_adjustment: pd.DataFrame, numbers=False
) -> pd.Series:
    """
    Combines original_rate series and rate_adjustment DataFrame, which has both 'multiply_value' and 'add_value' columns.
    - Multiplies original_rate with 'multiply_value' where provided.
    - Adds 'add_value' to original_rate where provided.
    - Ensures the result of addition is not less than 0.
    - Excludes cases where original_rate is missing.
    - If 'numbers' remains at False, normalizes rates to ensure that the sum of rates for each 'from' state is 1.
    """
    # Align original_rate and rate_adjustment DataFrame with a left join to retain all indices from original_rates
    original_rate, rate_adjustment = original_rate.align(rate_adjustment, join="left")

    # Fill missing values: multiply_value with 1 (neutral for multiplication), add_value with 0 (neutral for addition)
    rate_adjustment["multiply_value"].fillna(1, inplace=True)
    rate_adjustment["add_value"].fillna(0, inplace=True)

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

    # Create a flag to identify adjusted rates
    is_adjusted = (rate_adjustment["multiply_value"] != 1) | (
        rate_adjustment["add_value"] != 0
    )

    # Normalise rates that are not numbers (do not normalise entry rates as these can sum to more than 1)
    if not numbers:
        final_result = final_result.groupby(level="from", group_keys=False).apply(
            normalize_rates, is_adjusted
        )

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
                    transition_numbers = combine_rates(
                        transition_numbers, adjustment, numbers=True
                    )

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

    def next(
        self, population: np.ndarray, variance: float, step_days: int = 1
    ) -> NextPrediction:
        assert step_days > 0, "'step_days' must be greater than 0"
        for _ in range(step_days):
            # Cumulative variance propagation to reflect uncertainty growing linearly with time
            variance = variance + (
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
        variance = 0
        for i in iterator:
            prediction = predictor.next(population, variance, step_days=step_days)
            population = prediction.population
            predictions.append(population)
            variance = prediction.variance
            variances.append(variance)

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
