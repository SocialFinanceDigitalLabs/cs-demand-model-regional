from datetime import date
from functools import lru_cache
from itertools import product

import pandas as pd

from ssda903.config import AgeBrackets, Costs, PlacementCategories


class PopulationStats:
    def __init__(self, df: pd.DataFrame):
        self.__df = df

    @property
    def df(self):
        return self.__df

    @property
    def stock(self):
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

        # Resample to daily counts and forward-fill in missing days
        pops = pops.resample("D").first().fillna(method="ffill").fillna(0)

        # Add the missing age bins and fill with zeros

        return pops

    @lru_cache(maxsize=5)
    def stock_at(self, start_date) -> pd.Series:
        start_date = pd.to_datetime(start_date)

        index = self.stock.index.get_indexer([start_date], method="nearest")

        stock = self.stock.iloc[index[0]].T
        stock.name = start_date
        return stock

    @property
    def transitions(self):
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
        transitions = (
            transitions.unstack(level=["start_bin", "end_bin"])
            .fillna(0)
            .asfreq("D", fill_value=0)
        )

        return transitions

    @property
    def transition_combinations(self):
        """
        Used to calculate possible transitions with respect to age and placement
        """

        def get_number(data):
            """
            Gets the first age from age bins to sort the list of age bins
            """
            return int(data.split(" ")[0])

        def age_check(transition, bins):
            """
            Takes the sorted age bins and transitions and ensures the transitions are possible
            """
            beginning_age = transition[0].split("-")[0].strip()
            end_age = transition[1].split("-")[0].strip()

            beginning_place = transition[0].split("-")[-1].strip()
            end_place = transition[1].split("-")[-1].strip()

            start_bin_loc = bins.index(beginning_age)
            end_bin_loc = bins.index(end_age)

            # A transition is valid IFF the ages are the same and the placement is different
            # OR if the end age bin is one older than the start age bin, regardless of placement
            # This does not account for impsssible placements such as 5-10 supported
            if (beginning_age == end_age) & (beginning_place != end_place):
                return True
            elif end_bin_loc == start_bin_loc + 1:
                return True
            else:
                return False

        transitions = self.df.copy()

        beginning_placements = transitions["placement_type"].unique()
        end_placements = transitions["placement_type_after"].unique()

        age_bins = list(
            set(transitions["age_bin"].unique())
            | set(transitions["end_age_bin"].unique())
        )
        age_bins.remove(None)
        age_bins = sorted(age_bins, key=get_number)

        beginning_placement_product = list(product(beginning_placements, age_bins))
        all_beginning_placements = [
            f"{age} - {placement}" for placement, age in beginning_placement_product
        ]

        end_placement_product = list(product(end_placements, age_bins))
        all_end_placements = [
            f"{age} - {placement}" for placement, age in end_placement_product
        ]

        all_transitions = list(product(all_beginning_placements, all_end_placements))

        transition_possibility = [
            age_check(transition, age_bins) for transition in all_transitions
        ]

        possible_transitions = [
            transition
            for transition, possibility in zip(all_transitions, transition_possibility)
            if possibility == True
        ]

        return possible_transitions

    @lru_cache(maxsize=5)
    def raw_transition_rates(self, start_date: date, end_date: date):
        # Ensure we can calculate the transition rates by aligning the dataframes
        stock = self.stock.truncate(before=start_date, after=end_date)

        all_possible_transitions = self.transition_combinations

        stock.columns.name = "start_bin"
        transitions = self.transitions.truncate(before=start_date, after=end_date)

        # Calculate the transition rates
        stock, transitions = stock.align(transitions)
        transition_rates = transitions / stock.shift(1).fillna(method="bfill")
        transition_rates = transition_rates.fillna(0)

        # Use the mean rates
        transition_rates = transition_rates.mean(axis=0)
        transition_rates.name = "transition_rate"

        return transition_rates

    @property
    def ageing_out(self) -> pd.Series:
        """
        Returns the probability of ageing out from one bin to the other.
        """
        ageing_out = []
        for age_group in AgeBrackets:
            for pt in PlacementCategories:
                next_name = (
                    (age_group.next.value.label, pt.value.label)
                    if age_group.next
                    else tuple()
                )
                ageing_out.append(
                    {
                        "from": (age_group.value.label, pt.value.label),
                        "to": next_name,
                        "rate": age_group.value.daily_probability,
                    }
                )

        df = pd.DataFrame(ageing_out)
        df.set_index(["from", "to"], inplace=True)
        return df.rate

    @lru_cache(maxsize=5)
    def placement_proportions(
        self, reference_start_date: date, reference_end_date: date, **kwargs
    ):
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
    def daily_entrants(self, start_date: date, end_date: date) -> pd.Series:
        """
        Returns the number of entrants and the daily_probability of entrants for each age bracket and placement type.
        """
        start_date = pd.to_datetime(start_date)
        end_date = pd.to_datetime(end_date)

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

    def to_excel(self, output_file: str, start_date: date, end_date: date):
        with pd.ExcelWriter(output_file) as writer:
            self.stock_at(end_date).to_excel(writer, sheet_name="population")
            self.raw_transition_rates(start_date, end_date).to_excel(
                writer, sheet_name="transition_rates"
            )
            self.daily_entrants(start_date, end_date).to_excel(
                writer, sheet_name="daily_entrants"
            )
