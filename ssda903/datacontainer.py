import dataclasses
import logging
from datetime import date
from dateutil.relativedelta import relativedelta
from functools import cached_property
from typing import Optional
import numpy as np
import pandas as pd

from ssda903.config import (
    YEAR_IN_DAYS,
    AgeBrackets,
    Costs,
    EthnicitySubcategory,
    PlacementCategories,
)
from ssda903.data.ssda903 import SSDA903TableType
from ssda903.datastore import DataFile, DataStore, TableType

log = logging.getLogger(__name__)


class DemandModellingDataContainer:
    """
    A container for demand modelling data. Indexes data by table type. Provides methods for
    merging data to create a single, consistent dataset.
    """

    def __init__(self, datastore: DataStore):
        self.__datastore = datastore

        self.__file_info = []
        for file_info in datastore.files:
            if not file_info.metadata.table:
                table_type = self._detect_table_type(file_info)
                metadata = dataclasses.replace(file_info.metadata, table=table_type)
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

    def _detect_table_type(self, file_info: DataFile) -> Optional[TableType]:
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

        raise ValueError(f"Could not find table for table type {table_type}")

    def combined_datasets(self) -> pd.DataFrame:
        """
        Returns the combined view consisting of Episodes and Headers and creating a flag for UASC

        :return: A pandas DataFrame containing the combined view
        """
        # Merge header and UASC and keep most recent entry for CHILD
        # TODO: convert to datetimes should be done when the table is first read
        header = self.get_table(SSDA903TableType.HEADER)
        header["DOB"] = pd.to_datetime(header["DOB"], format="%d/%m/%Y")

        uasc = self.get_table(SSDA903TableType.UASC)
        uasc["DUC"] = pd.to_datetime(uasc["DUC"], format="%d/%m/%Y")

        merged = header.merge(
            uasc[["CHILD", "DUC", "YEAR"]], how="left", on=["CHILD", "YEAR"]
        )
        merged.sort_values(by="YEAR", ascending=False, inplace=True)
        merged = merged.drop_duplicates(subset=["CHILD"])

        # Merge into episodes file
        # TODO: convert to datetimes should be done when the table is first read
        episodes = self.get_table(SSDA903TableType.EPISODES)
        episodes["DECOM"] = pd.to_datetime(episodes["DECOM"], format="%d/%m/%Y")
        episodes["DEC"] = pd.to_datetime(episodes["DEC"], format="%d/%m/%Y")

        merged = episodes.merge(
            merged[["CHILD", "SEX", "DOB", "ETHNIC", "DUC"]], how="left", on="CHILD"
        )

        # create UASC flag if DUC
        merged["UASC"] = merged["DUC"].notna()

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
        # First we remove children who have no DOB, as this prevents us from knowing which age bucket to put them in
        combined.drop(combined[combined.DOB.isna()].index, inplace=True)
        log.debug(
            "%s records remaining after removing children with no DOB.",
            combined.shape,
        )

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

        # Mark episodes that represent only a change in legal status or placement status
        combined["Skip_Episode"] = np.where(
            (combined["RNE"].isin(["L", "T", "U"]))
            & (combined["CHILD"] == combined["CHILD"].shift(1))
            & (combined["DECOM"] == combined["DEC"].shift(1)),
            True,
            False,
        )

        # Keep episodes with Skip_Episode == FALSE, but maintain continuity in episode close info (DEC, REC, REASON_PLACE_CHANGE) with skipped episodes
        kept_rows = []
        skipped_episode = False
        last_skipped_dec = None
        last_skipped_rec = None
        last_skipped_rpc = None

        for index, row in combined.iterrows():
            if row["Skip_Episode"] == False:
                if skipped_episode == True:
                    kept_rows[-1]["DEC"] = last_skipped_dec
                    kept_rows[-1]["REC"] = last_skipped_rec
                    kept_rows[-1]["REASON_PLACE_CHANGE"] = last_skipped_rpc
                    skipped_episode = False
                kept_rows.append(row)
            else:
                skipped_episode = True
                last_skipped_dec = row["DEC"]
                last_skipped_rec = row["REC"]
                last_skipped_rpc = row["REASON_PLACE_CHANGE"]

        combined = pd.DataFrame(kept_rows)
        log.debug(
            "%s records remaining after removing episodes that do not represent new placements.",
            combined.shape,
        )

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
        combined = self._add_age_change_eps(combined)
        combined = self._add_placement_category(combined)
        combined = self._add_related_placement_type(
            combined, 1, "placement_type_before"
        )
        combined = self._add_related_placement_type(
            combined, -1, "placement_type_after"
        )
        combined = self._add_detailed_placement_category(combined)
        combined = self._add_detailed_ethnicity_column(combined)
        return combined

    @cached_property
    def data_start_date(self) -> date:
        """
        Returns the first date of the first SSDA903 return uploaded
        This will always be 1st April
        Note that this will not be the earliest date shown in DECOM, as a child's entry to care may have been prior to the start of the earliest return
        """
        # Find the minimum value in the 'DEC' column
        min_dec = self.combined_data["DEC"].min()

        # Extract the month and year from the min_dec date
        min_dec_month = min_dec.month
        min_dec_year = min_dec.year

        # Determine the start_date based on the month of min_dec
        if 4 <= min_dec_month <= 12:  # April to December
            data_start_date = date(min_dec_year, 4, 1)
        else:  # January to March
            data_start_date = date(min_dec_year - 1, 4, 1)

        return data_start_date

    @cached_property
    def data_end_date(self) -> date:
        """
        Returns the last date of the last SSDA903 return uploaded
        This will always be 31st March
        Note that this may not be the last date shown in the data, as no entry/transition/exit from care may have occurred on this day
        """
        max_dec_decom = self.combined_data[["DECOM", "DEC"]].max().max().date()

        # Extract the month and year from the max_dec_decom date
        max_dec_decom_month = max_dec_decom.month
        max_dec_decom_year = max_dec_decom.year

        # Determine the end_date based on the month of max_dec_decom
        if 4 <= max_dec_decom_month <= 12:  # April to December
            data_end_date = date(max_dec_decom_year + 1, 3, 31)
        else:  # January to March
            data_end_date = date(max_dec_decom_year, 3, 31)

        return data_end_date

    @cached_property
    def unique_las(self) -> pd.Series:
        return self.combined_data.LA.unique()

    @cached_property
    def unique_placement_types(self) -> pd.Series:
        return self.enriched_view.placement_type.unique()

    @cached_property
    def unique_age_bins(self) -> pd.Series:
        return self.enriched_view.age_bin.unique()

    @cached_property
    def unique_ethnicity(self) -> pd.Series:
        return self.enriched_view.ethnicity.unique()

    def _add_ages(self, combined: pd.DataFrame) -> pd.DataFrame:
        """
        Calculates the age of the child at the start and end of the episode and adds them as columns
        Age at end of episode is calculated regardless of whether the episode has ended
        WARNING: This method modifies the dataframe in place.
        """
        data_end_date = np.datetime64(self.data_end_date)
        combined["age"] = (combined["DECOM"] - combined["DOB"]).dt.days / YEAR_IN_DAYS
        combined["end_age"] = np.where(
            combined["DEC"].isna(),
            (data_end_date - combined["DOB"]).dt.days / YEAR_IN_DAYS,
            (combined["DEC"] - combined["DOB"]).dt.days / YEAR_IN_DAYS
        )
        return combined

    def _add_age_change_eps(self, combined: pd.DataFrame) -> pd.DataFrame:
        """
        Creates new rows for episodes where a child has crossed an age bin boundary
        Modifies rows to account for changes to start and end dates due to new rows
        Allocates age_bins for start and end of episodes
        WARNING: This method modifies the dataframe in place.
        """

        age_df = combined.copy()

        # Convert the AgeBrackets enum into a dataframe for more efficient access
        age_brackets_df = AgeBrackets.to_dataframe()
        age_bins = sorted(set(age_brackets_df["start"].to_list() + age_brackets_df["end"].to_list()))

        def get_age_bracket_attribute(df: pd.DataFrame, age_col: str, age_bins: str, return_col: str, attribute: str) -> pd.DataFrame:
            '''
            Returns an attribute relating to an age bracket based on an age column in a df

            Args:
                df (pd.DataFrame): Dataframe containing an age column (or an integer that stands in for age)
                age_col (str): The age column used to return the correct AgeBracket
                age_bins (str): The set of age_bins in AgeBrackets
                return_col (str): The name of the column to be created
                attribute (str): The attribute of the Enum to be returned e.g "start"

            Returns:
                pd.DataFrame: The original df with the mapped attribute as a new column
            '''
            # Assign the index of the age_brackets_df relevant to each row
            df["bracket_index"] = pd.cut(df[age_col], bins=age_bins, labels=age_brackets_df.index, right=False)
            # Map the attribute to the index
            df[return_col] = age_brackets_df.loc[df["bracket_index"], attribute].values
            
            return df.drop(columns=["bracket_index"])

        # Get bracket start value for the age bracket each episode starts in
        age_df = get_age_bracket_attribute(df=age_df, age_col="age", age_bins=age_bins, return_col="start_bracket", attribute="start")
        # Get all age boundaries crossed by each episode
        age_bounds = np.array(sorted([b.value.end for b in AgeBrackets if b.value.end]))
        mask = (age_bounds[None, :] > age_df["age"].values[:, None]) & (age_bounds[None, :] <= age_df["end_age"].values[:, None])
        age_df["age_brackets"] = [age_bounds[m].tolist() for m in mask]
        # Combine start brackets and boundaries into a single list to give all relevant start brackets for the episode
        age_df["age_brackets"] = age_df["start_bracket"].map(lambda x: [x]) + age_df["age_brackets"]

        # Expand each row into one row for each bracket
        age_df = age_df.explode("age_brackets", ignore_index=True)
        # Add end value for age bracket of each row
        age_df = get_age_bracket_attribute(df=age_df, age_col="age_brackets", age_bins=age_bins, return_col="end_bracket", attribute="end")

        # Update episode start information for relevant episodes
        # RNE = Reason for new episode
        age_condition = age_df["age_brackets"] > age_df["age"]

        age_df.loc[age_condition, "DECOM"] = age_df.loc[age_condition].apply(
            lambda row: row["DOB"] + relativedelta(years=int(row["age_brackets"])),
            axis=1
        )
        age_df.loc[age_condition, "RNE"] = "Age"
        age_df.loc[age_condition, "age"] = age_df.loc[age_condition, "age_brackets"]

        # Update episode end information for relevant episodes
        # Set DEC and end_age to the first day and age of the next age bracket so that end_age_bin will pick up the next age_bin
        end_age_condition = age_df["end_bracket"] < age_df["end_age"]

        age_df.loc[end_age_condition, "DEC"] = age_df.loc[end_age_condition].apply(
            lambda row: row["DOB"] + relativedelta(years=int(row["end_bracket"])),
            axis=1
        )
        age_df.loc[end_age_condition, "REC"] = "Age"
        age_df.loc[end_age_condition, "REASON_PLACE_CHANGE"] = ""
        age_df.loc[end_age_condition, "end_age"] = age_df.loc[end_age_condition,"end_bracket"]

        # Add age bin to the episodes
        age_df = get_age_bracket_attribute(df=age_df, age_col="age", age_bins=age_bins, return_col="age_bin", attribute="label")
        age_df = get_age_bracket_attribute(df=age_df, age_col="end_age", age_bins=age_bins, return_col="end_age_bin", attribute="label")
    
        combined = age_df

        log.debug(
            "%s records after adding episodes based on age transitions.",
            combined.shape,
        )
        return combined

    def _add_related_placement_type(
        self, combined: pd.DataFrame, offset: int, new_column_name: str
    ) -> pd.DataFrame:
        """
        Adds the related placement type, -1 for following, or 1 for preceeding.

        WARNING: This method modifies the dataframe in place.
        """
        combined = combined.sort_values(["CHILD", "DECOM", "DEC"], na_position="first")

        # Group by child and set next/preceding placement based on offset
        # Set any blank values (where next/preceding episode is not the same child) as Not in Care
        combined[new_column_name] = (
            combined.groupby("CHILD")["placement_type"]
            .shift(offset)
            .fillna(PlacementCategories.NOT_IN_CARE.value.label)
        )

        # Create offset mask - this will identify rows where the offset row is the same CHILD and where there is a break between episodes
        offset_mask = combined["CHILD"] == combined["CHILD"].shift(offset)
        if offset > 0:
            offset_mask &= combined["DECOM"] != combined["DEC"].shift(offset)
        else:
            offset_mask &= combined["DEC"] != combined["DECOM"].shift(offset)

        # Apply offset mask - this will overwrite any non-continuous care episodes with not in care rather than the adjacent episode
        combined.loc[
            offset_mask, new_column_name
        ] = PlacementCategories.NOT_IN_CARE.value.label

        # For next episodes (offset = -1) where the current episode hasn't ended, set next placement as None
        if offset == -1:
            combined.loc[combined["DEC"].isna(), new_column_name] = "None"

        return combined

    def _add_placement_category(self, combined: pd.DataFrame) -> pd.DataFrame:
        """
        Adds placement category for

        WARNING: This method modifies the dataframe in place.
        """
        placement_type_map = PlacementCategories.get_placement_type_map()
        combined["placement_type"] = combined["PLACE"].apply(
            lambda x: placement_type_map.get(x, PlacementCategories.OTHER.value).label
        )
        return combined

    def _add_detailed_placement_category(self, combined: pd.DataFrame) -> pd.DataFrame:
        """
        Adds placement category for

        WARNING: This method modifies the dataframe in place.
        """
        placement_type_map = Costs.get_placement_type_map()

        def lookup_placement_type(row):
            # Try to match (placement_type, place_provider)
            key = (row["PLACE"], row["PLACE_PROVIDER"])
            if key in placement_type_map:
                return placement_type_map[key].label
            # Fall back to matching (placement_type, "")
            fallback_key = (row["PLACE"], "")
            return placement_type_map.get(
                fallback_key, PlacementCategories.OTHER.value
            ).label

        combined["placement_type_detail"] = combined.apply(
            lookup_placement_type, axis=1
        )

        return combined

    def _add_detailed_ethnicity_column(self, combined: pd.DataFrame) -> pd.DataFrame:
        # Load the JSON file containing the ethnicity codes and subcategories
        combined["ethnicity"] = combined["ETHNIC"].map(
            lambda x: EthnicitySubcategory[x].value
        )

        return combined
