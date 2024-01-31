import dataclasses
import logging
from datetime import date
from functools import cached_property
from typing import Generator, Optional, Tuple

import pandas as pd

from cs_demand_model.config import Config
from cs_demand_model.data.ssda903 import SSDA903TableType
from cs_demand_model.datastore import DataFile, DataStore, TableType
from functools import lru_cache

log = logging.getLogger(__name__)


class DemandModellingDataContainer:
    """
    A container for demand modelling data. Indexes data by year and table type. Provides methods for
    merging data to create a single, consistent dataset.
    """

    def __init__(self, datastore: DataStore, config: Config):
        self.__datastore = datastore
        self.__config = config

        self.__file_info = []
        for file_info in datastore.files:
            if not file_info.metadata.table:
                table_type, year = self._detect_table_type(file_info)
                metadata = dataclasses.replace(
                    file_info.metadata, table=table_type, year=year
                )
                file_info = dataclasses.replace(file_info, metadata=metadata)

            # We only care about Header and Episodes
            if file_info.metadata.table in [
                SSDA903TableType.HEADER,
                SSDA903TableType.EPISODES,
            ]:
                self.__file_info.append(file_info)

    @property
    def file_info(self):
        return self.__file_info

    @property
    def config(self) -> Config:
        return self.__config

    def _detect_table_type(
        self, file_info: DataFile
    ) -> Tuple[Optional[TableType], Optional[int]]:
        """
        Detect the table type of a file by reading the first line of the file and looking for a
        known table type.

        :param file_info: The file to detect the table type for
        :return: The table type or None if not found.
        """
        try:
            df = self.__datastore.to_dataframe(file_info)
        except Exception as ex:
            log.warning("Failed to read file %s: %s", file_info, ex)
            return None, None

        table_type = None
        for table_type in SSDA903TableType:
            table_class = table_type.value
            fields = table_class.fields
            if len(set(fields) - set(df.columns)) == 0:
                break

        year = None
        if table_type == SSDA903TableType.EPISODES:
            df["DECOM"] = pd.to_datetime(df["DECOM"], dayfirst=True)
            year = max(df["DECOM"].dt.year)

        return table_type, year

    @property
    def first_year(self):
        return min(
            [info.metadata.year for info in self.__file_info if info.metadata.year]
        )

    @property
    def last_year(self):
        return max(
            [info.metadata.year for info in self.__file_info if info.metadata.year]
        )

    def get_table(self, year: int, table_type: TableType) -> pd.DataFrame:
        """
        Gets a table for a given year and table type.

        :param year: The year to get the table for
        :param table_type: The table type to get
        :return: A pandas DataFrame containing the table data
        """
        for info in self.__file_info:
            metadata = info.metadata
            if metadata.year == year and metadata.table == table_type:
                return self.__datastore.to_dataframe(info)

        raise ValueError(
            f"Could not find table for year {year} and table type {table_type}"
        )

    def get_tables_by_type(
        self, table_type: TableType
    ) -> Generator[pd.DataFrame, None, None]:
        for info in self.__file_info:
            if info.metadata.table == table_type:
                yield self.__datastore.to_dataframe(info)

    def combined_year(self, year: int) -> pd.DataFrame:
        """
        Returns the combined view for the year consisting of Episodes and Headers

        :param year: The year to get the combined view for
        :return: A pandas DataFrame containing the combined view
        """
        header = list(self.get_tables_by_type(SSDA903TableType.HEADER))
        if len(list(header)) == 0:
            raise ValueError("No headers found")
        header = pd.concat(header)
        header = header.drop_duplicates(subset=["CHILD"])

        episodes = self.get_table(year, SSDA903TableType.EPISODES)

        # TODO: This should be done when the table is first read
        header["DOB"] = pd.to_datetime(header["DOB"], format="%d/%m/%Y")
        episodes["DECOM"] = pd.to_datetime(episodes["DECOM"], format="%d/%m/%Y")
        episodes["DEC"] = pd.to_datetime(episodes["DEC"], format="%d/%m/%Y")

        merged = header.merge(
            episodes, how="inner", on="CHILD", suffixes=("_header", "_episodes")
        )

        return merged

    @cached_property
    def combined_data(self) -> pd.DataFrame:
        """
        Returns the combined view for all years consisting of Episodes and Headers. Runs some sanity checks
        as

        :param combined: A pandas DataFrame containing the combined view - if not provided, it will simply concatenate
                         the values for all years in this container
        :return: A pandas DataFrame containing the combined view
        """
        combined = pd.concat(
            [
                self.combined_year(year)
                for year in range(self.first_year, self.last_year + 1)
            ]
        )

        # Just do some basic data validation checks
        assert not combined["CHILD"].isna().any()
        assert not combined["DECOM"].isna().any()

        # Then clean up the episodes
        # We first sort by child, decom and dec, and make sure NAs are first (for dropping duplicates)
        combined.sort_values(
            ["CHILD", "DECOM", "DEC"], inplace=True, na_position="first"
        )

        # If a child has two episodes starting on the same day (usually if NA in one year and then done in next)
        # keep the latest non-NA finish date
        combined.drop_duplicates(["CHILD", "DECOM"], keep="last", inplace=True)
        log.debug(
            "%s records remaining after removing episodes that start on the same date.",
            combined.shape,
        )

        # If a child has two episodes with the same end date, keep the longer one.
        # This also works for open episodes - if there are two open, keep the larger one.
        combined.drop_duplicates(["CHILD", "DEC"], keep="first", inplace=True)
        log.debug(
            "%s records remaining after removing episodes that end on the same date.",
            combined.shape,
        )

        # If a child has overlapping episodes, shorten the earlier one
        decom_next = combined.groupby("CHILD")["DECOM"].shift(-1)
        change_ix = combined["DEC"].isna() | combined["DEC"].gt(decom_next)
        combined.loc[change_ix, "DEC"] = decom_next[change_ix]

        return combined

    @cached_property
    def enriched_view(self) -> pd.DataFrame:
        """
        Adds several additional columns to the combined view to support the model calculations.

        * age - the age of the child at the start of the episode
        * age_end - the age of the child at the end of the episode

        """
        combined = self.combined_data
        combined = self._add_ages(combined)
        combined = self._add_age_bins(combined)
        combined = self._add_placement_category(combined)
        combined = self._add_related_placement_type(
            combined, 1, "placement_type_before"
        )
        combined = self._add_related_placement_type(
            combined, -1, "placement_type_after"
        )
        return combined

    @cached_property
    def start_date(self) -> date:
        return self.combined_data[["DECOM", "DEC"]].min().min()

    @cached_property
    def end_date(self) -> date:
        return self.combined_data[["DECOM", "DEC"]].max().max()

    def _add_ages(self, combined: pd.DataFrame) -> pd.DataFrame:
        """
        Calculates the age of the child at the start and end of the episode and adds them as columns

        WARNING: This method modifies the dataframe in place.
        """
        combined["age"] = (
            combined["DECOM"] - combined["DOB"]
        ).dt.days / self.__config.year_in_days
        combined["end_age"] = (
            combined["DEC"] - combined["DOB"]
        ).dt.days / self.__config.year_in_days
        return combined

    def _add_age_bins(self, combined: pd.DataFrame) -> pd.DataFrame:
        """
        Adds age bins for the child at the start and end of the episode and adds them as columns

        WARNING: This method modifies the dataframe in place.
        """
        AgeBracket = self.__config.AgeBrackets
        combined["age_bin"] = combined["age"].apply(AgeBracket.bracket_for_age)
        combined["end_age_bin"] = combined["end_age"].apply(AgeBracket.bracket_for_age)
        return combined

    def _add_related_placement_type(
        self, combined: pd.DataFrame, offset: int, new_column_name: str
    ) -> pd.DataFrame:
        """
        Adds the related placement type, -1 for following, or 1 for preceeding.

        WARNING: This method modifies the dataframe in place.
        """
        PlacementCategories = self.__config.PlacementCategories

        combined = combined.sort_values(["CHILD", "DECOM", "DEC"], na_position="first")

        combined[new_column_name] = (
            combined.groupby("CHILD")["placement_type"]
            .shift(offset)
            .fillna(PlacementCategories.NOT_IN_CARE)
        )

        offset_mask = combined["CHILD"] == combined["CHILD"].shift(offset)
        if offset > 0:
            offset_mask &= combined["DECOM"] != combined["DEC"].shift(offset)
        else:
            offset_mask &= combined["DEC"] != combined["DECOM"].shift(offset)
        combined.loc[offset_mask, new_column_name] = PlacementCategories.NOT_IN_CARE
        return combined

    def _add_placement_category(self, combined: pd.DataFrame) -> pd.DataFrame:
        """
        Adds placement category for

        WARNING: This method modifies the dataframe in place.
        """
        PlacementCategories = self.__config.PlacementCategories
        combined["placement_type"] = combined["PLACE"].apply(
            lambda x: PlacementCategories.placement_type_map.get(
                x, PlacementCategories.OTHER
            )
        )
        return combined

    @lru_cache(maxsize=5)
    def daily_entrants(self, start_date: date, end_date: date) -> pd.Series:
        """
        Returns the number of entrants and the daily_probability of entrants for each age bracket and placement type.
        """
        PlacementCategories = self.config.PlacementCategories
        start_date = pd.to_datetime(start_date)
        end_date = pd.to_datetime(end_date)

        df = self.enriched_view

        # Only look at episodes starting in analysis period
        df = df[(df["DECOM"] >= start_date) & (df["DECOM"] <= end_date)].copy()

        df["to"] = df.apply(lambda c: (c.age_bin.name, c.placement_type.name), axis=1)

        # Group by age bin and placement type
        df = (
            df[df["placement_type_before"] == PlacementCategories.NOT_IN_CARE]
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

    @property
    def ageing_out(self) -> pd.Series:
        """
        Returns the probability of ageing out from one bin to the other.
        """
        ageing_out = []
        for age_group in self.config.AgeBrackets:
            for pt in self.config.PlacementCategories:
                next_name = (
                    (age_group.next.name, pt.name) if age_group.next else tuple()
                )
                ageing_out.append(
                    {
                        "from": (age_group.name, pt.name),
                        "to": next_name,
                        "rate": age_group.daily_probability,
                    }
                )

        df = pd.DataFrame(ageing_out)
        df.set_index(["from", "to"], inplace=True)
        return df.rate

    @property
    def to_model(self):
        df = self.enriched_view.copy()
        df["start_bin"] = df.apply(
            lambda c: (c.age_bin.name, c.placement_type.name), axis=1
        )
        df["end_bin"] = df.apply(
            lambda c: (c.age_bin.name, c.placement_type_after.name), axis=1
        )
        df = df.rename(columns={"DECOM": "start_date", "DEC": "end_date"})
        return df
