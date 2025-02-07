import unittest

import pandas as pd

from ssda903.population_stats import PopulationStats


class TestDailyEntryProbability(unittest.TestCase):
    def setUp(self):
        """Set up test data before each test."""
        data = {
            "CHILD": [290, 519, 519, 519],
            "DECOM": pd.to_datetime(
                ["2016-11-19", "2017-03-09", "2017-09-14", "2018-03-26"]
            ),
            "RNE": ["T", "P", "S", "A"],
            "LS": ["D1", "J2", "D1", "D1"],
            "CIN": ["N5", "N6", "N8", "N8"],
            "PLACE": ["U5", "U4", "U5", "U5"],
            "PLACE_PROVIDER": ["PR4", "PR1", "PR4", "PR4"],
            "age_bin": ["16 to 18+", "10 to 16", "10 to 16", "16 to 18+"],
            "end_age_bin": ["16 to 18+", "10 to 16", "16 to 18+", "16 to 18+"],
            "placement_type": ["Fostering", "Fostering", "Fostering", "Fostering"],
            "placement_type_before": [
                "Not in care",
                "Not in care",
                "Fostering",
                "Fostering",
            ],
            "placement_type_after": [
                "Not in care",
                "Fostering",
                "Fostering",
                "Not in care",
            ],
            "placement_type_detail": [
                "Fostering (IFA)",
                "Fostering (In-house)",
                "Fostering (IFA)",
                "Fostering (IFA)",
            ],
            "ethnicity": [
                "White and Black Caribbean",
                "Any other Asian background",
                "Any other Asian background",
                "Any other Asian background",
            ],
        }
        self.sample_data = pd.DataFrame(data)

        self.data_start_date = pd.to_datetime(self.sample_data["DECOM"].min())
        self.data_end_date = pd.to_datetime(self.sample_data["DECOM"].max())

    def test_output_is_series(self):
        """Test if function output is a pandas Series."""
        stats = PopulationStats(
            df=self.sample_data,
            data_start_date=self.data_start_date,
            data_end_date=self.sample_data["DECOM"].max(),
        )
        result = stats.daily_entrants(
            reference_start_date=self.data_start_date,
            reference_end_date=self.data_end_date,
        )
        self.assertIsInstance(result, pd.Series, "Output is not a pandas Series")

    def test_series_name(self):
        """
        Test if the Series name is 'daily_entry_probability'.
        This is a requirement for validation on DynamicRateForm
        """
        stats = PopulationStats(
            df=self.sample_data,
            data_start_date=self.data_start_date,
            data_end_date=self.data_end_date,
        )

        daily_entrants = stats.daily_entrants(
            reference_start_date=self.data_start_date,
            reference_end_date=self.data_end_date,
        )
        result = daily_entrants.name
        self.assertEqual(result, "daily_entry_probability", "Series name is incorrect")
