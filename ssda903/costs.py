from dataclasses import dataclass
from decimal import Decimal, getcontext
from typing import Iterable, Optional, Union

import pandas as pd
from dateutil.relativedelta import relativedelta

from ssda903.config import Costs, PlacementCategories
from ssda903.multinomial import Prediction
from ssda903.population_stats import PopulationStats

# Set the precision for decimal operations
getcontext().prec = 6


@dataclass
class CostForecast:
    costs: pd.DataFrame
    proportions: pd.DataFrame
    cost_summary: pd.DataFrame
    summary_table: pd.DataFrame
    population: pd.DataFrame


def get_cost_items_for_category(category_label: str):
    """
    Takes a placement category label and returns related enum costs in a list
    """
    cost_items = []
    for cost in Costs:
        if cost.value.category.label == category_label:
            cost_items.append(cost.value)
    return cost_items


def normalize_proportions(cost_items, proportion_adjustment):
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
        else:
            remaining_total += item.defaults.proportion

    total_proportion = adjustment_total + remaining_total

    if total_proportion == 1:
        # If the total is exactly 1, return the proportions as they are
        for item in cost_items:
            if item.label in proportion_adjustment.index:
                normalised_proportions[item.label] = proportion_adjustment[item.label]
            else:
                normalised_proportions[item.label] = item.defaults.proportion
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
                proportion = Decimal(str(item.defaults.proportion)) * Decimal(
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
    cost_adjustment: Union[pd.Series, Iterable[pd.Series]] = None,
    proportion_adjustment: Union[pd.Series, Iterable[pd.Series]] = None,
    inflation: Union[bool] = None,
    inflation_rate: Union[float] = None,
) -> CostForecast:
    """
    This will take a population via a Prediction or PopulationStats object and transform it to a cost.
    """
    if isinstance(data, Prediction):
        forecast_population = data.population
    elif isinstance(data, PopulationStats):
        forecast_population = data.stock

    proportions = pd.Series(dtype="float64")
    costs = pd.Series(dtype="float64")

    # Filter out columns that contain the not in care population
    columns_to_keep = [
        col for col in forecast_population.columns if "Not in care" not in col
    ]
    # Return the dataframe with only the in care population
    forecast_population = forecast_population[columns_to_keep]

    cost_forecast = pd.DataFrame(index=forecast_population.index)
    proportion_population = pd.DataFrame(index=forecast_population.index)
    start_date = forecast_population.index[0]

    for column in forecast_population.columns:
        # for each column, create a new series where we will sum the total cost output

        for category in PlacementCategories:
            # for each category, check if the category label is in the column header
            if category.value.label in column:
                cost_items = get_cost_items_for_category(category.value.label)

                if proportion_adjustment is not None:
                    # Apply proportion adjustments
                    normalised_proportions = normalize_proportions(
                        cost_items, proportion_adjustment
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
                    # add original weekly cost to costs output
                    costs[cost_item.label] = cost_per_week

                    if (
                        proportion_adjustment is not None
                        and cost_item.label in normalised_proportions.index
                    ):
                        proportion = normalised_proportions[cost_item.label]
                    else:
                        proportion = cost_item.defaults.proportion
                    # add proportion to proportions output
                    proportions[cost_item.label] = proportion

                    if inflation is True:
                        anniversary = start_date
                        for i, current_date in enumerate(forecast_population.index):
                            # for each year that passes, add interest to the cost per day
                            if current_date == anniversary + relativedelta(years=1):
                                cost_per_day = apply_inflation_to_cost_item(
                                    cost_per_day, inflation_rate
                                )
                                anniversary = current_date

                            if cost_item.label in cost_forecast.columns:
                                if pd.isna(
                                    cost_forecast.at[current_date, cost_item.label]
                                ):
                                    cost_forecast.at[current_date, cost_item.label] = (
                                        forecast_population.at[current_date, column]
                                        * cost_per_day
                                        * proportion
                                    )
                                else:
                                    cost_forecast.at[current_date, cost_item.label] += (
                                        forecast_population.at[current_date, column]
                                        * cost_per_day
                                        * proportion
                                    )
                            else:
                                cost_forecast.at[current_date, cost_item.label] = (
                                    forecast_population.at[current_date, column]
                                    * cost_per_day
                                    * proportion
                                )
                    else:
                        # for each cost item, multiply by cost per day and proportion, then sum together
                        if cost_item.label in cost_forecast.columns:
                            cost_forecast[cost_item.label] += (
                                forecast_population[column] * cost_per_day * proportion
                            )
                        else:
                            cost_forecast[cost_item.label] = (
                                forecast_population[column] * cost_per_day * proportion
                            )
                    # for each cost item, multiply forecast population by proportion, then sum together for proportioned population
                    if cost_item.label in proportion_population.columns:
                        proportion_population[cost_item.label] += (
                            forecast_population[column] * proportion
                        )
                    else:
                        proportion_population[cost_item.label] = (
                            forecast_population[column] * proportion
                        )

    summary_table = resample_summary_table(cost_forecast)
    return CostForecast(
        cost_forecast, proportions, costs, summary_table, proportion_population
    )
