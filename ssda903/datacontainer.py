import dataclasses
import logging
from datetime import date
from functools import cached_property
from typing import Generator, Optional, Tuple

import pandas as pd
import numpy as np

from ssda903.config import Config
from ssda903.data.ssda903 import SSDA903TableType
from ssda903.datastore import DataFile, DataStore, TableType
from functools import lru_cache

log = logging.getLogger(__name__)


class DemandModellingDataContainer:
    """
    A container for demand modelling data. Indexes data by table type. Provides methods for
    merging data to create a single, consistent dataset.
    """

    def __init__(self, datastore: DataStore, config: Config):
        self.__datastore = datastore
        self.__config = config

        self.__file_info = []
        for file_info in datastore.files:
            if not file_info.metadata.table:
                table_type = self._detect_table_type(file_info)
                metadata = dataclasses.replace(
                    file_info.metadata, table=table_type
                )
                file_info = dataclasses.replace(file_info, metadata=metadata)

            # We only care about Header, Episodes and UASC
            if file_info.metadata.table in [
                SSDA903TableType.HEADER,
                SSDA903TableType.EPISODES,
                SSDA903TableType.UASC,
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
    ) -> Optional[TableType]:
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
            return None

        table_type = None
        for table_type in SSDA903TableType:
            table_class = table_type.value
            fields = table_class.fields
            if len(set(fields) - set(df.columns)) == 0:
                break

        if table_type == SSDA903TableType.EPISODES:
            df["DECOM"] = pd.to_datetime(df["DECOM"], dayfirst=True)

        return table_type

    def get_table(self, table_type: TableType) -> pd.DataFrame:
        """
        Gets a table for a table type.

        :param table_type: The table type to get
        :return: A pandas DataFrame containing the table data
        """
        for info in self.__file_info:
            metadata = info.metadata
            if metadata.table == table_type:
                return self.__datastore.to_dataframe(info)

        raise ValueError(
            f"Could not find table for table type {table_type}"
        )

    def get_tables_by_type(
        self, table_type: TableType
    ) -> Generator[pd.DataFrame, None, None]:
        for info in self.__file_info:
            if info.metadata.table == table_type:
                yield self.__datastore.to_dataframe(info)


    def combined_datasets(self) -> pd.DataFrame:
        """
        Returns the combined view consisting of Episodes and Headers and creating a flag for UASC

        :return: A pandas DataFrame containing the combined view
        """
        header = self.get_table(SSDA903TableType.HEADER)
        header = header.drop_duplicates(subset=["CHILD"])
        header = header.drop(["LA","YEAR"], axis='columns')

        episodes = self.get_table(SSDA903TableType.EPISODES)

        uasc = self.get_table(SSDA903TableType.UASC)
        uasc = uasc.drop(["LA","YEAR"], axis='columns')
        uasc = uasc.drop_duplicates(subset=["CHILD"])

        # TODO: This should be done when the table is first read
        header["DOB"] = pd.to_datetime(header["DOB"], format="%d/%m/%Y")
        episodes["DECOM"] = pd.to_datetime(episodes["DECOM"], format="%d/%m/%Y")
        episodes["DEC"] = pd.to_datetime(episodes["DEC"], format="%d/%m/%Y")
        uasc["DUC"] = pd.to_datetime(episodes["DEC"], format="%d/%m/%Y")

        merged = header.merge(
            episodes, how="inner", on="CHILD", suffixes=("_header", "_episodes")
        )

        merged = merged.merge(
            uasc[["CHILD","DUC"]], how="left", on="CHILD"
        )

        #create UASC flag if DECOM is less than DUC
        merged["UASC"] = np.where(merged['DECOM'] < merged['DUC'], 1, 0)

        return merged


    @cached_property
    def combined_data(self) -> pd.DataFrame:
        """
        Returns the combined view consisting of Episodes and Headers. Runs some sanity checks
        as

        :param combined: A pandas DataFrame containing the combined view - if not provided, it will simply concatenate
                         the values in this container
        :return: A pandas DataFrame containing the combined view
        """
        combined = self.combined_datasets()

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
    