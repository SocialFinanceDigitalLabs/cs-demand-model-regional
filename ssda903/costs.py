from dataclasses import dataclass
from decimal import Decimal, getcontext
from typing import Iterable, Optional, Union

import pandas as pd

from ssda903.config import Costs, PlacementCategories
from ssda903.multinomial import Prediction

# Set the precision for decimal operations
getcontext().prec = 6


@dataclass
class CostForecast:
    population: pd.DataFrame
    proportions: pd.DataFrame
    costs: pd.DataFrame


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
    This function makes sure the proportions for each category sum to 1

    It will prioritise proportions in the proportion adjustment series, eg
    If proportion adjustments sum to less than 1 but total proportions sum to
    more than 1, this will be adjusted via changing proportions not in the
    adjustment series.

    If the adjustment total sums to more than 1, other proportions will
    scale to 0 and the proportions in the adjustment series will be scaled
    to sum to 1.
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

    if adjustment_total >= 1:
        # Set remaining proportions to 0 and scale down adjustment proportions
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
        # Adjust remaining proportions to make the total sum to 1
        scale_factor = (
            (Decimal("1") - Decimal(str(adjustment_total)))
            / Decimal(str(remaining_total))
            if remaining_total > 0
            else 0
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


def forecast_costs(
    data: Prediction,
    cost_adjustment: Union[pd.Series, Iterable[pd.Series]] = None,
    proportion_adjustment: Union[pd.Series, Iterable[pd.Series]] = None,
    # inflation? True/false
) -> CostForecast:
    """
    This will take a population and translate it to a cost.
    """

    forecast_population = data.population
    processed_categories = set()
    proportions = pd.Series(dtype="float64")
    costs = pd.Series(dtype="float64")

    # Filter out columns that contain the not in care population
    columns_to_keep = [
        col for col in forecast_population.columns if "Not in care" not in col
    ]
    # Return the dataframe with only the in care population
    forecast_population = forecast_population[columns_to_keep]

    cost_forecast = pd.DataFrame(index=forecast_population.index)
    for column in forecast_population.columns:
        # for each column, create a new series where we will sum the total cost output
        total_cost_series = pd.Series(0, index=forecast_population.index)

        for category in PlacementCategories:
            # for each category, check if the category label is in the column header
            if (
                category.value.label in column
                and category.value.label not in processed_categories
            ):
                processed_categories.add(category.value.label)
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
                        cost_per_day = cost_adjustment[cost_item.label]
                    else:
                        cost_per_day = cost_item.defaults.cost_per_day
                    if (
                        proportion_adjustment is not None
                        and cost_item.label in normalised_proportions.index
                    ):
                        proportion = normalised_proportions[cost_item.label]
                    else:
                        proportion = cost_item.defaults.proportion
                    # for each cost item, multiply by cost per day and proportion, then sum together
                    total_cost_series += (
                        forecast_population[column] * cost_per_day * proportion
                    )
                    proportions[cost_item.label] = proportion
                    costs[cost_item.label] = cost_per_day
        cost_forecast[column] = total_cost_series
    return CostForecast(cost_forecast, proportions, costs)
