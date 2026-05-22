import unittest
from datetime import date

import numpy as np
import pandas as pd
import pandas.testing as pdt

from ssda903.population_stats import _calculate_raw_transition_rates

class TestCalculateRawTransitionRates(unittest.TestCase):
    def setUp(self):
        # 4 consecutive days
        self.dates = pd.to_datetime(
            ["2026-01-01", "2026-01-02", "2026-01-03", "2026-01-04"]
        )

    def _make_transitions_df(self, data, index=None, cols=None):
        """
        Helper: create transitions DataFrame with MultiIndex columns (start_bin, end_bin).
        data: list/array-like rows
        cols: list of (start_bin, end_bin) tuples
        """
        if index is None:
            index = self.dates
        if cols is None:
            cols = [("A", "B")]

        df = pd.DataFrame(data, index=index)
        df.columns = pd.MultiIndex.from_tuples(cols, names=["start_bin", "end_bin"])
        return df

    def test_normal_case_mean_rate(self):
        # stock is by start_bin (single-level columns)
        stock = pd.DataFrame({"A": [10, 10, 10, 10]}, index=self.dates)

        # transitions are by (start_bin, end_bin)
        transitions = self._make_transitions_df(
            data=[
                [0],  # day1
                [1],  # day2
                [2],  # day3
                [1],  # day4
            ],
            cols=[("A", "B")],
        )

        unique_transitions = pd.MultiIndex.from_tuples(
            [("A", "B")], names=["start_bin", "end_bin"]
        )

        out = _calculate_raw_transition_rates(
            stock=stock,
            transitions=transitions,
            unique_transitions=unique_transitions,
            reference_start_date=self.dates[1].date(),
            reference_end_date=self.dates[3].date(),
        )

        expected = pd.Series(
            {("A", "B"): (1 / 10 + 2 / 10 + 1 / 10) / 3},
            name="transition_rate",
        )
        expected.index = unique_transitions

        pdt.assert_series_equal(out.loc[unique_transitions], expected)

    def test_truncation_uses_prev_day_outside_ref_dates(self):
        # day1 stock=10, day2 stock=0; we set ref dates starting at day2
        # denom for day2 should be previous day (day1) stock=10 because shift occurs BEFORE truncation
        stock = pd.DataFrame({"A": [10, 0, 0, 0]}, index=self.dates)

        transitions = self._make_transitions_df(
            data=[
                [0],
                [5],
                [0],
                [0],
            ],
            cols=[("A", "B")],
        )

        unique_transitions = pd.MultiIndex.from_tuples(
            [("A", "B")], names=["start_bin", "end_bin"]
        )

        out = _calculate_raw_transition_rates(
            stock=stock,
            transitions=transitions,
            unique_transitions=unique_transitions,
            reference_start_date=self.dates[1].date(),
            reference_end_date=self.dates[1].date(),
        )

        self.assertAlmostEqual(out.loc[("A", "B")], 0.5)

    def test_reference_start_is_first_day_becomes_zero(self):
        # On the first day, shifted stock is NaN; daily rate is NaN; mean is NaN; fillna->0
        stock = pd.DataFrame({"A": [10, 10, 10, 10]}, index=self.dates)

        transitions = self._make_transitions_df(
            data=[
                [3],
                [0],
                [0],
                [0],
            ],
            cols=[("A", "B")],
        )

        unique_transitions = pd.MultiIndex.from_tuples(
            [("A", "B")], names=["start_bin", "end_bin"]
        )

        out = _calculate_raw_transition_rates(
            stock=stock,
            transitions=transitions,
            unique_transitions=unique_transitions,
            reference_start_date=self.dates[0].date(),
            reference_end_date=self.dates[0].date(),
        )

        self.assertEqual(out.loc[("A", "B")], 0.0)

    def test_zero_over_zero_is_ignored_and_becomes_zero(self):
        # prev_stock = 0, transitions = 0 => 0/0 -> NaN; mean -> NaN; fillna->0
        stock = pd.DataFrame({"A": [0, 0, 0, 0]}, index=self.dates)
        transitions = self._make_transitions_df(
            data=[[0], [0], [0], [0]],
            cols=[("A", "B")],
        )

        unique_transitions = pd.MultiIndex.from_tuples(
            [("A", "B")], names=["start_bin", "end_bin"]
        )

        out = _calculate_raw_transition_rates(
            stock=stock,
            transitions=transitions,
            unique_transitions=unique_transitions,
            reference_start_date=self.dates[1].date(),
            reference_end_date=self.dates[3].date(),
        )

        self.assertEqual(out.loc[("A", "B")], 0.0)

    def test_positive_over_zero_raises_valueerror(self):
        # if stock_shift == 0 (meaning prior day stock 0) but transitions > 0, raise.
        stock = pd.DataFrame({"A": [0, 0, 10, 10]}, index=self.dates)
        transitions = self._make_transitions_df(
            data=[[0], [2], [0], [0]],
            cols=[("A", "B")],
        )

        unique_transitions = pd.MultiIndex.from_tuples(
            [("A", "B")], names=["start_bin", "end_bin"]
        )

        with self.assertRaises(ValueError):
            _calculate_raw_transition_rates(
                stock=stock,
                transitions=transitions,
                unique_transitions=unique_transitions,
                reference_start_date=self.dates[1].date(),
                reference_end_date=self.dates[1].date(),
            )

    def test_reindex_adds_missing_transitions_as_zero(self):
        stock = pd.DataFrame({"A": [10, 10, 10, 10]}, index=self.dates)
        transitions = self._make_transitions_df(
            data=[[0], [1], [0], [0]],
            cols=[("A", "B")],
        )

        unique_transitions = pd.MultiIndex.from_tuples(
            [("A", "B"), ("A", "C")], names=["start_bin", "end_bin"]
        )

        out = _calculate_raw_transition_rates(
            stock=stock,
            transitions=transitions,
            unique_transitions=unique_transitions,
            reference_start_date=self.dates[1].date(),
            reference_end_date=self.dates[3].date(),
        )

        self.assertIn(("A", "C"), out.index)
        self.assertEqual(out.loc[("A", "C")], 0.0)
