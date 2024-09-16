from dataclasses import dataclass
from decimal import Decimal, getcontext
from typing import Iterable, Union

import pandas as pd
from dateutil.relativedelta import relativedelta

from ssda903.config import Costs, PlacementCategories
from ssda903.multinomial import Prediction
from ssda903.population_stats import PopulationStats
from ssda903.utils import get_cost_items_for_category

# Set the precision for decimal operations
getcontext().prec = 6


@dataclass
class CostForecast:
    costs: pd.DataFrame
    proportions: pd.DataFrame
    cost_summary: pd.DataFrame
    summary_table: pd.DataFrame
    proportional_population: pd.DataFrame


def normalize_proportions(cost_items, historic_proportions, proportion_adjustment):
    """
    This function makes sure the proportions for each category sum to 1.

    It will prioritize proportions in the proportion adjustment series, e.g.,
    If proportion adjustments sum to less than 1 but total proportions sum to
    more than 1, this will be adjusted via changing proportions not in the
    adjustment series.

    If the adjustment total sums to more than 1, other proportions will
    scale to 0 and the proportions in the adjustment series will be scaled
    to sum to 1.

    If the total proportions sum to less than 1, keep adjustment proportions
    unchanged and scale up the remaining proportions.
    """
    adjustment_total = 0
    remaining_total = 0
    normalised_proportions = pd.Series(dtype="float64")

    # Calculate the total of adjustment proportions and remaining proportions
    for item in cost_items:
        if item.label in proportion_adjustment.index:
            adjustment_total += proportion_adjustment[item.label]
        elif item.label in historic_proportions.index:
            remaining_total += historic_proportions[item.label]
        else:
            pass

    total_proportion = adjustment_total + remaining_total

    if total_proportion == 1:
        # If the total is exactly 1, return the proportions as they are
        for item in cost_items:
            if item.label in proportion_adjustment.index:
                normalised_proportions[item.label] = proportion_adjustment[item.label]
            elif item.label in historic_proportions.index:
                normalised_proportions[item.label] = historic_proportions[item.label]
            else:
                normalised_proportions[item.label] = 0
    elif adjustment_total >= 1 or remaining_total == 0:
        # For when adjustments are >= 1 and there are remaining; or adjustments are < 1 and there are no remaining
        # Scale adjustments up or down and set any remaining to 0
        scale_factor = Decimal("1") / Decimal(str(adjustment_total))
        for item in cost_items:
            if item.label in proportion_adjustment.index:
                proportion = float(
                    Decimal(str(proportion_adjustment[item.label]))
                    * Decimal(str(scale_factor))
                )
            else:
                proportion = 0
            normalised_proportions[item.label] = proportion
    else:
        # For when adjustments are < 1 and there are remaining, remaining must be scaled up or down
        scale_factor = (Decimal("1") - Decimal(str(adjustment_total))) / Decimal(
            str(remaining_total)
        )
        for item in cost_items:
            if item.label in proportion_adjustment.index:
                proportion = proportion_adjustment[item.label]
            else:
                proportion = Decimal(str(historic_proportions[item.label])) * Decimal(
                    str(scale_factor)
                )
            normalised_proportions[item.label] = float(proportion)

    return normalised_proportions


def resample_summary_table(summary_table):
    """
    Takes daily dataframe and resamples to represent quarterly periods.
    """

    summary_table.index = pd.to_datetime(summary_table.index)
    summary_table = summary_table.resample("Q").sum()

    # Convert the DatetimeIndex to a PeriodIndex representing quarters
    summary_table.index = summary_table.index.to_period("Q")

    # Optionally convert the PeriodIndex to a string format if preferred
    summary_table.index = summary_table.index.strftime("Q%q-%Y")
    summary_table = summary_table.round(2)
    return summary_table


def apply_inflation_to_cost_item(cost_per_day, inflation_rate):
    new_cost_per_day = Decimal(str(cost_per_day)) * (
        (Decimal("1") + Decimal(str(inflation_rate)))
    )
    return float(new_cost_per_day)


def convert_population_to_cost(
    data: Union[Prediction, PopulationStats],
    historic_proportions: Union[pd.Series, Iterable[pd.Series]] = None,
    cost_adjustment: Union[pd.Series, Iterable[pd.Series]] = None,
    proportion_adjustment: Union[pd.Series, Iterable[pd.Series]] = None,
    inflation: Union[bool] = None,
    inflation_rate: Union[float] = None,
) -> CostForecast:
    """
    This will take a population via a Prediction or PopulationStats object and transform it to a cost.
    """
    if isinstance(data, Prediction):
        input_population = data.population
    elif isinstance(data, PopulationStats):
        input_population = data.stock

    proportions = pd.Series(dtype="float64")
    cost_summary = pd.Series(dtype="float64")

    # Filter out columns that contain the not in care population
    columns_to_keep = [
        col for col in input_population.columns if "Not in care" not in col
    ]
    # Return the dataframe with only the in care population
    input_population = input_population[columns_to_keep]

    costs = pd.DataFrame(index=input_population.index)
    proportional_population = pd.DataFrame(index=input_population.index)
    start_date = input_population.index[0]

    for column in input_population.columns:
        # for each column, create a new series where we will sum the total cost output

        for category in PlacementCategories:
            # for each category, check if the category label is in the column header
            if category.value.label in column:
                cost_items = get_cost_items_for_category(category.value.label)

                if proportion_adjustment is not None:
                    # Apply proportion adjustments
                    normalised_proportions = normalize_proportions(
                        cost_items, historic_proportions, proportion_adjustment
                    )

                for cost_item in cost_items:
                    # check if there are cost adjustments and if so, take from this table
                    if (
                        cost_adjustment is not None
                        and cost_item.label in cost_adjustment.index
                    ):
                        cost_per_week = cost_adjustment[cost_item.label]
                    else:
                        cost_per_week = cost_item.defaults.cost_per_week
                    # work out daily cost
                    cost_per_day = cost_per_week / 7
                    # add original weekly cost to cost_summary output
                    cost_summary[cost_item.label] = cost_per_week

                    if (
                        proportion_adjustment is not None
                        and cost_item.label in normalised_proportions.index
                    ):
                        proportion = normalised_proportions[cost_item.label]
                    elif cost_item.label in historic_proportions.index:
                        proportion = historic_proportions[cost_item.label]
                    # add proportion to proportions output
                    proportions[cost_item.label] = proportion

                    if inflation is True:
                        anniversary = start_date
                        for i, current_date in enumerate(input_population.index):
                            # for each year that passes, add interest to the cost per day
                            if current_date == anniversary + relativedelta(years=1):
                                cost_per_day = apply_inflation_to_cost_item(
                                    cost_per_day, inflation_rate
                                )
                                anniversary = current_date

                            if cost_item.label in costs.columns:
                                if pd.isna(costs.at[current_date, cost_item.label]):
                                    costs.at[current_date, cost_item.label] = (
                                        input_population.at[current_date, column]
                                        * cost_per_day
                                        * proportion
                                    )
                                else:
                                    costs.at[current_date, cost_item.label] += (
                                        input_population.at[current_date, column]
                                        * cost_per_day
                                        * proportion
                                    )
                            else:
                                costs.at[current_date, cost_item.label] = (
                                    input_population.at[current_date, column]
                                    * cost_per_day
                                    * proportion
                                )
                    else:
                        # for each cost item, multiply by cost per day and proportion, then sum together
                        if cost_item.label in costs.columns:
                            costs[cost_item.label] += (
                                input_population[column] * cost_per_day * proportion
                            )
                        else:
                            costs[cost_item.label] = (
                                input_population[column] * cost_per_day * proportion
                            )
                    # for each cost item, multiply forecast population by proportion, then sum together for proportioned population
                    if cost_item.label in proportional_population.columns:
                        proportional_population[cost_item.label] += (
                            input_population[column] * proportion
                        )
                    else:
                        proportional_population[cost_item.label] = (
                            input_population[column] * proportion
                        )

    summary_table = resample_summary_table(costs)
    return CostForecast(
        costs, proportions, cost_summary, summary_table, proportional_population
    )


def convert_historic_population_to_cost(
    input_population: Union[Prediction, PopulationStats],
    cost_adjustment: Union[pd.Series, Iterable[pd.Series]] = None,
) -> pd.DataFrame:
    """
    This will take a detailed historic population - proportion_population output from placement_proportions - and convert to a cost
    """

    costs = pd.DataFrame(index=input_population.index)

    for column in input_population.columns:
        # for each column, create a new series where we will sum the total cost output

        for cost in Costs:
            # for each category, check if the category label is in the column header
            if cost.value.label in column:
                cost_item = cost.value

                if (
                    cost_adjustment is not None
                    and cost_item.label in cost_adjustment.index
                ):
                    cost_per_week = cost_adjustment[cost_item.label]
                else:
                    cost_per_week = cost_item.defaults.cost_per_week
                # work out daily cost
                cost_per_day = cost_per_week / 7

                # for each cost item, multiply by cost per day
                costs[cost_item.label] = input_population[column] * cost_per_day

    return costs
