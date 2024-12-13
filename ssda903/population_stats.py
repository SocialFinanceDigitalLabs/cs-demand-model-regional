from datetime import date
from functools import lru_cache

import pandas as pd

from ssda903.config import Costs, PlacementCategories


class PopulationStats:
    """
    Transforms an episode-level table from datacontainer into a series of tables showing the following:
    - stock: child populations by model state by day for the total time period
    - transitions: state transitions by day e.g. 10-15 Fostering->16-18 Fostering for the total time period
    - raw transition rates: a rate for each state transition for a defined reference period
    - placement proportions: the proportion of placements within a placement category (as defined by PlacementCategories enum) belonging to more granular placement types for a defined reference period
    - entry rates: the rate of entry per day for each model state for a defined reference period
    """

    def __init__(self, df: pd.DataFrame):
        self.__df = df

    @property
    def df(self):
        return self.__df

    @property
    def stock(self, data_end_date: date, data_start_date: date):
        """
        Calculates the daily transitions for each age bin and placement type by
        finding all the transitions (start or end of episode), summing to get total populations for each
        day and then resampling to get the daily populations.
        """
        df = self.df.copy()

        df["bin"] = df.apply(
            lambda c: f"{c.age_bin} - {c.placement_type.capitalize()}",
            axis=1,
        )

        endings = df.groupby(["DEC", "bin"]).size()
        endings.name = "nof_decs"

        beginnings = df.groupby(["DECOM", "bin"]).size()
        beginnings.name = "nof_decoms"

        endings.index.names = ["date", "bin"]
        beginnings.index.names = ["date", "bin"]

        pops = pd.merge(
            left=beginnings,
            right=endings,
            left_index=True,
            right_index=True,
            how="outer",
        )

        pops = pops.fillna(0).sort_values("date")

        pops = (pops["nof_decoms"] - pops["nof_decs"]).groupby(["bin"]).cumsum()

        pops = pops.unstack(level=1)

        # Ensure the last date of the return is present
        if data_end_date > pops.index.max():
            # Add the row to the end of the dataframe with this date
            pops.loc[data_end_date] = None

        # Resample to daily counts and forward-fill in missing days
        pops = pops.resample("D").first().fillna(method="ffill").fillna(0)

        # Truncate the dataset to cut out dates earlier than the start date and later than the end date
        pops = pops.truncate(before=data_start_date, after=data_end_date)

        return pops

    @lru_cache(maxsize=5)
    def stock_at(self, date) -> pd.Series:
        """
        Returns the stock on a given date
        """
        date = pd.to_datetime(date)

        index = self.stock.index.get_indexer([date], method="nearest")

        stock = self.stock.iloc[index[0]].T
        stock.name = date
        return stock

    @property
    def transitions(self, data_end_date: date, data_start_date: date):
        """
        Returns the number of transitions per day for each model state for the total time period in the input data
        Transitions include exits from care e.g. 5-10 Residential -> Not in care
        Transitions do not include entrants to care
        """
        transitions = self.df.copy()
        transitions["start_bin"] = transitions.apply(
            lambda c: f"{c.age_bin} - {c.placement_type.capitalize()}",
            axis=1,
        )
        transitions["end_bin"] = transitions.apply(
            lambda c: f"{c.end_age_bin} - {c.placement_type_after.capitalize()}",
            axis=1,
        )
        transitions = transitions.groupby(["start_bin", "end_bin", "DEC"]).size()
        transitions = transitions.unstack(level=["start_bin", "end_bin"])

        # Ensure the last date of the return is present
        if data_end_date > transitions.index.max():
            # Add the row to the end of the dataframe with this date
            transitions.loc[data_end_date] = None

        transitions = transitions.fillna(0).asfreq("D", fill_value=0)

        # Truncate the dataset to cut out dates earlier than the start date and later than the end date
        transitions = transitions.truncate(before=data_start_date, after=data_end_date)

        return transitions

    @lru_cache(maxsize=5)
    def raw_transition_rates(
        self, reference_start_date: date, reference_end_date: date
    ):
        """
        Calculates transition rates for each transition using:
        - stock
        - transitions
        - reference dates
        """
        # Ensure we can calculate the transition rates by aligning the dataframes
        stock = self.stock.truncate(
            before=reference_start_date, after=reference_end_date
        )
        stock.columns.name = "start_bin"
        transitions = self.transitions.truncate(
            before=reference_start_date, after=reference_end_date
        )

        # Calculate the transition rates
        stock, transitions = stock.align(transitions)
        transition_rates = transitions / stock.shift(1).fillna(method="bfill")
        transition_rates = transition_rates.fillna(0)

        # Use the mean rates
        transition_rates = transition_rates.mean(axis=0)
        transition_rates.name = "transition_rate"

        return transition_rates

    @lru_cache(maxsize=5)
    def placement_proportions(
        self, reference_start_date: date, reference_end_date: date, **kwargs
    ):
        """
        Calculates the proportion of placements in each placement category that were from a more granular set of placements for the historic data over a defined reference period
        - placement categories from PlacementCategories enum
        """
        start_date = pd.to_datetime(reference_start_date)
        end_date = pd.to_datetime(reference_end_date)

        df = self.df.copy()

        df["bin"] = df.apply(
            lambda c: f"{c.placement_type_detail}",
            axis=1,
        )

        endings = df.groupby(["DEC", "bin"]).size()
        endings.name = "nof_decs"

        beginnings = df.groupby(["DECOM", "bin"]).size()
        beginnings.name = "nof_decoms"

        endings.index.names = ["date", "bin"]
        beginnings.index.names = ["date", "bin"]

        pops = pd.merge(
            left=beginnings,
            right=endings,
            left_index=True,
            right_index=True,
            how="outer",
        )

        pops = pops.fillna(0).sort_values("date")

        pops = (pops["nof_decoms"] - pops["nof_decs"]).groupby(["bin"]).cumsum()

        pops = pops.unstack(level=1)

        # Resample to daily counts and forward-fill in missing days
        pops = pops.resample("D").first().fillna(method="ffill").fillna(0)

        proportion_population = pops.truncate(before=start_date, after=end_date)

        total_pops = pops.sum()

        proportion_series = pd.Series(dtype="float64")

        for category in PlacementCategories:
            # fetch cost items for each category
            cost_items = Costs.get_cost_items_for_category(category.value.label)
            # create empty series to store related placement populations
            placement_series = pd.Series(dtype="float64")
            for cost_item in cost_items:
                # if cost item is in the total_pops index, store value to placement series
                if cost_item.label in total_pops.index:
                    placement_series[cost_item.label] = total_pops[cost_item.label]
            # normalise populations
            placement_series = placement_series / placement_series.sum()
            # add normalised population to proportion series
            proportion_series = pd.concat([proportion_series, placement_series])

        return proportion_series, proportion_population

    @lru_cache(maxsize=5)
    def daily_entrants(
        self, reference_start_date: date, reference_end_date: date
    ) -> pd.Series:
        """
        Returns the daily probability of entrants for each model state
        """
        start_date = pd.to_datetime(reference_start_date)
        end_date = pd.to_datetime(reference_end_date)

        df = self.df

        # Only look at episodes starting in analysis period
        df = df[(df["DECOM"] >= start_date) & (df["DECOM"] <= end_date)].copy()
        df["to"] = df.apply(
            lambda c: f"{c.age_bin} - {c.placement_type.capitalize()}",
            axis=1,
        )

        # Group by age bin and placement type
        df = (
            df[
                df["placement_type_before"]
                == PlacementCategories.NOT_IN_CARE.value.label
            ]
            .groupby(["to"])
            .size()
        )
        df.name = "entrants"

        # Reset index
        df = df.reset_index()

        df["period_duration"] = (end_date - start_date).days
        df["daily_entry_probability"] = df["entrants"] / df["period_duration"]
        df["from"] = df.period_duration.apply(lambda x: tuple())

        df = df.set_index(["from", "to"])

        return df.daily_entry_probability
