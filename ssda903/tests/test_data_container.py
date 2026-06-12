import unittest
from dataclasses import dataclass
from enum import Enum
from unittest.mock import patch

import numpy as np
import pandas as pd

from ssda903.datacontainer import (
    DemandModellingDataContainer,
    _ensure_numeric,
    _get_age_bracket_attribute,
    _prepare_age_brackets,
    _update_boundary_dates,
)


class TestRemoveRedundantEpisodes(unittest.TestCase):
    def test__remove_redundant_episodes(self):
        dummy = None

        # Test 1: 2 rows; 1 episode to keep and 1 redundant; non-null data in DEC, REC, REASON_PLACE_CHANGE moved up
        sample_1 = {
            "CHILD": [1, 1],
            "DECOM": ["01/01/2020", "01/02/2020"],
            "DEC": ["01/02/2020", "01/03/2020"],
            "RNE": ["S", "L"],
            "REC": ["X", "E15"],
            "REASON_PLACE_CHANGE": ["A", "B"],
        }
        sample_1_df = pd.DataFrame(sample_1)
        sample_1_df["DECOM"] = pd.to_datetime(sample_1_df["DECOM"], format="%d/%m/%Y")
        sample_1_df["DEC"] = pd.to_datetime(sample_1_df["DEC"], format="%d/%m/%Y")

        test_result_1 = DemandModellingDataContainer._remove_redundant_episodes(
            dummy, sample_1_df
        )
        self.assertEqual(len(test_result_1), 1)
        first_row = test_result_1.iloc[0]
        self.assertEqual(first_row["DEC"].strftime("%d/%m/%Y"), "01/03/2020")
        self.assertEqual(first_row["RNE"], "S")
        self.assertEqual(first_row["DECOM"].strftime("%d/%m/%Y"), "01/01/2020")
        self.assertEqual(first_row["REC"], "E15")
        self.assertEqual(first_row["REASON_PLACE_CHANGE"], "B")

        # Test 2: 4 rows; 2 episodes to keep and 2 redundant; null data in DEC moved up
        sample_2 = {
            "CHILD": [2, 2, 2, 2],
            "DECOM": ["01/01/2020", "01/02/2020", "01/03/2020", "01/04/2020"],
            "DEC": ["01/02/2020", "01/03/2020", "01/04/2020", None],
            "RNE": ["S", "P", "T", "L"],
            "REC": ["X", "X", "E15", "E17"],
            "REASON_PLACE_CHANGE": ["A", "B", "C", "D"],
        }
        sample_2_df = pd.DataFrame(sample_2)
        sample_2_df["DECOM"] = pd.to_datetime(sample_2_df["DECOM"], format="%d/%m/%Y")
        sample_2_df["DEC"] = pd.to_datetime(sample_2_df["DEC"], format="%d/%m/%Y")

        test_result_2 = DemandModellingDataContainer._remove_redundant_episodes(
            dummy, sample_2_df
        )
        self.assertEqual(len(test_result_2), 2)
        second_row = test_result_2.iloc[1]
        self.assertTrue(pd.isna(second_row["DEC"]))
        self.assertEqual(second_row["RNE"], "P")
        self.assertEqual(second_row["DECOM"].strftime("%d/%m/%Y"), "01/02/2020")
        self.assertEqual(second_row["REC"], "E17")
        self.assertEqual(second_row["REASON_PLACE_CHANGE"], "D")

        # Test 3: 3 rows; 2 children, 1 with only a "U" row (so can't be removed as only one), 1 with "U", "P" concurrent, none removed as "U" is first
        sample_3 = {
            "CHILD": [2, 3, 3],
            "DECOM": ["01/01/2020", "01/02/2020", "01/03/2020"],
            "DEC": ["01/02/2020", "01/03/2020", None],
            "RNE": ["U", "U", "B"],
            "REC": ["X", "X", "E15"],
            "REASON_PLACE_CHANGE": ["A", "B", "C"],
        }
        sample_3_df = pd.DataFrame(sample_3)
        sample_3_df["DECOM"] = pd.to_datetime(sample_3_df["DECOM"], format="%d/%m/%Y")
        sample_3_df["DEC"] = pd.to_datetime(sample_3_df["DEC"], format="%d/%m/%Y")

        test_result_3 = DemandModellingDataContainer._remove_redundant_episodes(
            dummy, sample_3_df
        )
        self.assertEqual(len(test_result_3), 3)
        second_row = test_result_3.iloc[1]
        self.assertEqual(second_row["DEC"].strftime("%d/%m/%Y"), "01/03/2020")
        self.assertEqual(second_row["RNE"], "U")
        self.assertEqual(second_row["DECOM"].strftime("%d/%m/%Y"), "01/02/2020")
        self.assertEqual(second_row["REC"], "X")
        self.assertEqual(second_row["REASON_PLACE_CHANGE"], "B")

        # Test 4: 4 rows; 2 episodes to keep and 2 redundant; data from final row carried up
        sample_4 = {
            "CHILD": [4, 4, 4, 4],
            "DECOM": ["01/01/2020", "01/02/2020", "01/03/2020", "01/04/2020"],
            "DEC": ["01/02/2020", "01/03/2020", "01/04/2020", "01/05/2020"],
            "RNE": ["S", "P", "T", "L"],
            "REC": ["X", "X", "X", "E15"],
            "REASON_PLACE_CHANGE": ["A", "B", "C", "D"],
        }
        sample_4_df = pd.DataFrame(sample_4)
        sample_4_df["DECOM"] = pd.to_datetime(sample_4_df["DECOM"], format="%d/%m/%Y")
        sample_4_df["DEC"] = pd.to_datetime(sample_4_df["DEC"], format="%d/%m/%Y")

        test_result_4 = DemandModellingDataContainer._remove_redundant_episodes(
            dummy, sample_4_df
        )
        self.assertEqual(len(test_result_4), 2)
        second_row = test_result_4.iloc[1]
        self.assertEqual(second_row["DEC"].strftime("%d/%m/%Y"), "01/05/2020")
        self.assertEqual(second_row["RNE"], "P")
        self.assertEqual(second_row["DECOM"].strftime("%d/%m/%Y"), "01/02/2020")
        self.assertEqual(second_row["REC"], "E15")
        self.assertEqual(second_row["REASON_PLACE_CHANGE"], "D")

        # Test 5: 2 rows; 2 episodes to keep as "T" episode is non-contiguous with earlier "P" episode
        sample_5 = {
            "CHILD": [5, 5],
            "DECOM": ["01/01/2020", "01/03/2020"],
            "DEC": ["01/02/2020", None],
            "RNE": ["P", "T"],
            "REC": ["X", "E15"],
            "REASON_PLACE_CHANGE": ["A", "B"],
        }
        sample_5_df = pd.DataFrame(sample_5)
        sample_5_df["DECOM"] = pd.to_datetime(sample_5_df["DECOM"], format="%d/%m/%Y")
        sample_5_df["DEC"] = pd.to_datetime(sample_5_df["DEC"], format="%d/%m/%Y")

        test_result_5 = DemandModellingDataContainer._remove_redundant_episodes(
            dummy, sample_5_df
        )
        self.assertEqual(len(test_result_5), 2)
        first_row = test_result_5.iloc[0]
        self.assertEqual(first_row["DEC"].strftime("%d/%m/%Y"), "01/02/2020")
        self.assertEqual(first_row["RNE"], "P")
        self.assertEqual(first_row["DECOM"].strftime("%d/%m/%Y"), "01/01/2020")
        self.assertEqual(first_row["REC"], "X")
        self.assertEqual(first_row["REASON_PLACE_CHANGE"], "A")

        # Test 6: 3 rows; same child; first is "U" so can't be removed; second "U" is removed with info flowing to first, third "B" is not changed
        sample_6 = {
            "CHILD": [6, 6, 6],
            "DECOM": ["01/01/2020", "01/02/2020", "01/03/2020"],
            "DEC": ["01/02/2020", "01/03/2020", None],
            "RNE": ["U", "U", "B"],
            "REC": ["X", "E15", None],
            "REASON_PLACE_CHANGE": ["A", "B", "C"],
        }
        sample_6_df = pd.DataFrame(sample_6)
        sample_6_df["DECOM"] = pd.to_datetime(sample_6_df["DECOM"], format="%d/%m/%Y")
        sample_6_df["DEC"] = pd.to_datetime(sample_6_df["DEC"], format="%d/%m/%Y")

        test_result_6 = DemandModellingDataContainer._remove_redundant_episodes(
            dummy, sample_6_df
        )
        self.assertEqual(len(test_result_6), 2)
        first_row = test_result_6.iloc[0]
        self.assertEqual(first_row["DEC"].strftime("%d/%m/%Y"), "01/03/2020")
        self.assertEqual(first_row["RNE"], "U")
        self.assertEqual(first_row["DECOM"].strftime("%d/%m/%Y"), "01/01/2020")
        self.assertEqual(first_row["REC"], "E15")
        self.assertEqual(first_row["REASON_PLACE_CHANGE"], "B")
        second_row = test_result_6.iloc[1]
        self.assertTrue(pd.isna(second_row["DEC"]))
        self.assertEqual(second_row["RNE"], "B")
        self.assertEqual(second_row["DECOM"].strftime("%d/%m/%Y"), "01/03/2020")
        self.assertTrue(pd.isna(second_row["REC"]))
        self.assertEqual(second_row["REASON_PLACE_CHANGE"], "C")


class TestEnsureNumeric(unittest.TestCase):
    def test_returns_numeric_series_unchanged(self):
        series = pd.Series([1, 2, 3], dtype="int64")

        result = _ensure_numeric(series)

        pd.testing.assert_series_equal(result, series)

    def test_converts_numeric_strings(self):
        series = pd.Series(["1", "2", "3"])

        result = _ensure_numeric(series)

        expected = pd.Series([1, 2, 3], dtype="int64")
        pd.testing.assert_series_equal(result, expected)

    def test_raises_for_non_numeric_values(self):
        series = pd.Series(["1", "two", "3"])

        with self.assertRaises(ValueError):
            _ensure_numeric(series)


class TestGetAgeBracketAttribute(unittest.TestCase):
    def setUp(self):
        self.age_brackets_df = pd.DataFrame(
            {
                "start": [0, 5, 10],
                "end": [5, 10, 18],
                "label": ["0-4", "5-9", "10-17"],
            }
        )
        self.age_bins = np.array([0, 5, 10, 18])

    def test_maps_label_from_age(self):
        df = pd.DataFrame({"age": [1, 6, 12]})

        result = _get_age_bracket_attribute(
            df=df.copy(),
            age_col="age",
            age_bins=self.age_bins,
            age_brackets_df=self.age_brackets_df,
            return_col="age_bin",
            attribute="label",
        )

        expected = pd.Series(["0-4", "5-9", "10-17"], name="age_bin")
        pd.testing.assert_series_equal(result["age_bin"], expected)

    def test_boundary_value_uses_next_bin_when_right_false(self):
        df = pd.DataFrame({"age": [5, 10]})

        result = _get_age_bracket_attribute(
            df=df.copy(),
            age_col="age",
            age_bins=self.age_bins,
            age_brackets_df=self.age_brackets_df,
            return_col="start_bracket",
            attribute="start",
        )

        expected = pd.Series([5, 10], name="start_bracket")
        pd.testing.assert_series_equal(result["start_bracket"], expected)


class TestPrepareAgeBrackets(unittest.TestCase):
    def test_includes_start_bracket_and_crossed_boundaries(self):
        df = pd.DataFrame(
            {
                "age": [4, 6, 0],
                "end_age": [11, 8, 5],
                "start_bracket": [0, 5, 0],
            }
        )
        age_bounds = np.array([5, 10])

        result = _prepare_age_brackets(df.copy(), age_bounds)

        self.assertEqual(result.loc[0, "age_brackets"].tolist(), [0, 5, 10])
        self.assertEqual(result.loc[1, "age_brackets"].tolist(), [5])
        self.assertEqual(result.loc[2, "age_brackets"].tolist(), [0, 5])


class TestUpdateBoundaryDates(unittest.TestCase):
    def test_updates_date_using_anchor_year_plus_boundary(self):
        df = pd.DataFrame(
            {
                "DOB": pd.to_datetime(["2010-06-15"]),
                "age_brackets": [5],
                "DECOM": pd.to_datetime(["2020-01-01"]),
            }
        )
        condition = pd.Series([True])

        result = _update_boundary_dates(
            df=df.copy(),
            condition=condition,
            anchor_date="DOB",
            boundary="age_brackets",
            input_date="DECOM",
        )

        self.assertEqual(result.loc[0, "DECOM"], pd.Timestamp("2015-06-15"))

    def test_clips_29_feb_to_28_feb_in_non_leap_year(self):
        df = pd.DataFrame(
            {
                "DOB": pd.to_datetime(["2012-02-29"]),
                "age_brackets": [1],
                "DECOM": pd.to_datetime(["2020-01-01"]),
            }
        )
        condition = pd.Series([True])

        result = _update_boundary_dates(
            df=df.copy(),
            condition=condition,
            anchor_date="DOB",
            boundary="age_brackets",
            input_date="DECOM",
        )

        self.assertEqual(result.loc[0, "DECOM"], pd.Timestamp("2013-02-28"))

    def test_rows_not_matching_condition_are_unchanged(self):
        df = pd.DataFrame(
            {
                "DOB": pd.to_datetime(["2010-06-15"]),
                "age_brackets": [5],
                "DECOM": pd.to_datetime(["2020-01-01"]),
            }
        )
        condition = pd.Series([False])

        result = _update_boundary_dates(
            df=df.copy(),
            condition=condition,
            anchor_date="DOB",
            boundary="age_brackets",
            input_date="DECOM",
        )

        self.assertEqual(result.loc[0, "DECOM"], pd.Timestamp("2020-01-01"))


@dataclass(frozen=True)
class _Bracket:
    start: int
    end: int
    label: str


class FakeAgeBrackets(Enum):
    ONE_TO_FIVE = _Bracket(1, 5, "1-5")
    FIVE_TO_TEN = _Bracket(5, 10, "5-10")
    TEN_TO_SIXTEEN = _Bracket(10, 16, "10-16")

    @classmethod
    def to_dataframe(cls):
        return pd.DataFrame(
            {
                "start": [1, 5, 10],
                "end": [5, 10, 16],
                "label": ["1-5", "5-10", "10-16"],
            }
        )


class TestAddAgeChangeEps(unittest.TestCase):
    @patch("ssda903.datacontainer.AgeBrackets", FakeAgeBrackets)
    def test_splits_episode_when_age_boundary_crossed(self):
        dummy = None
        combined = pd.DataFrame(
            {
                "DOB": pd.to_datetime(["2010-06-15"]),
                "age": [4],
                "end_age": [6],
                "DECOM": pd.to_datetime(["2014-01-01"]),
                "DEC": pd.to_datetime(["2016-12-31"]),
                "RNE": ["P"],
                "REC": ["X1"],
                "REASON_PLACE_CHANGE": ["CREQB"],
            }
        )

        result = DemandModellingDataContainer._add_age_change_eps(None, combined.copy())

        self.assertEqual(len(result), 2)

        # first segment should end at age boundary
        first = result.iloc[0]
        second = result.iloc[1]

        self.assertEqual(first["end_age"], 5)
        self.assertEqual(first["REC"], "Age")
        self.assertEqual(first["REASON_PLACE_CHANGE"], "")
        self.assertEqual(first["DEC"], pd.Timestamp("2015-06-15"))

        # second segment should start at age boundary
        self.assertEqual(second["age"], 5)
        self.assertEqual(second["RNE"], "Age")
        self.assertEqual(second["DECOM"], pd.Timestamp("2015-06-15"))
        self.assertEqual(second["REC"], "X1")
        self.assertEqual(second["REASON_PLACE_CHANGE"], "CREQB")
        self.assertEqual(second["DEC"], pd.Timestamp("2016-12-31"))

    @patch("ssda903.datacontainer.AgeBrackets", FakeAgeBrackets)
    def test_does_not_split_when_no_boundary_crossed(self):
        dummy = None
        combined = pd.DataFrame(
            {
                "DOB": pd.to_datetime(["2010-06-15"]),
                "age": [5],
                "end_age": [6],
                "DECOM": pd.to_datetime(["2015-06-15"]),
                "DEC": pd.to_datetime(["2016-06-15"]),
                "RNE": ["S"],
                "REC": ["X1"],
                "REASON_PLACE_CHANGE": ["PLACE"],
            }
        )

        result = DemandModellingDataContainer._add_age_change_eps(None, combined.copy())

        self.assertEqual(len(result), 1)
        self.assertEqual(result.loc[0, "RNE"], "S")
        self.assertEqual(result.loc[0, "REC"], "X1")
        self.assertEqual(result.loc[0, "DEC"], pd.Timestamp("2016-06-15"))
