import numpy as np
import pandas as pd
from django.test import TestCase

from dm_regional_app.forms import DynamicRateForm


class DynamicRateFormTest(TestCase):
    def setUp(self):
        # Setup initial dataframe and initial data
        self.dataframe = pd.DataFrame(
            {"from": ["A", "B", "C"], "to": ["X", "Y", "Z"], "rate": [1.5, 2.0, 3.0]}
        ).set_index(["from", "to"])

        # Initial data containing values for multiply and add
        self.initial_data = pd.DataFrame(
            {"multiply_value": [1.2, None, 1.8], "add_value": [None, 0.8, None]},
            index=pd.MultiIndex.from_tuples([("A", "X"), ("B", "Y"), ("C", "Z")]),
        )

    def test_initialize_fields_with_initial_data(self):
        # Test form initialization with initial values
        form = DynamicRateForm(dataframe=self.dataframe, initial_data=self.initial_data)

        # Check that the initial values are set correctly
        self.assertEqual(form.fields["multiply_('A', 'X')"].initial, 1.2)
        self.assertTrue(np.isnan(form.fields["add_('A', 'X')"].initial))
        self.assertEqual(form.fields["add_('B', 'Y')"].initial, 0.8)

    def test_form_submission_valid(self):
        # Test form submission with valid data
        form_data = {
            "multiply_('A', 'X')": 1.3,
            "add_('A', 'X')": "",
            "multiply_('B', 'Y')": "",
            "add_('B', 'Y')": 0.9,
            "multiply_('C', 'Z')": "",
            "add_('C', 'Z')": 0.4,
        }

        form = DynamicRateForm(
            form_data, dataframe=self.dataframe, initial_data=self.initial_data
        )

        # Check if the form is valid
        self.assertTrue(form.is_valid())

        # After cleaning, check if cleaned_data is as expected
        cleaned_data = form.clean()
        self.assertEqual(cleaned_data["multiply_('A', 'X')"], 1.3)
        self.assertTrue(cleaned_data["multiply_('B', 'Y')"] == None)
        self.assertEqual(cleaned_data["add_('B', 'Y')"], 0.9)

    def test_form_submission_with_invalid_data(self):
        # Test form submission with invalid data (both multiply and add are filled)
        form_data = {
            "multiply_('A', 'X')": 1.3,
            "add_('A', 'X')": 0.5,  # Both fields filled
            "multiply_('B', 'Y')": "",
            "add_('B', 'Y')": 0.9,
            "multiply_('C', 'Z')": "",
            "add_('C', 'Z')": "",
        }

        form = DynamicRateForm(
            data=form_data, dataframe=self.dataframe, initial_data=self.initial_data
        )

        # Check if the form is invalid due to both multiply and add fields being filled
        self.assertFalse(form.is_valid())

        # Ensure that the error messages reflect the correct fields
        self.assertIn("multiply_('A', 'X')", form.errors)
        self.assertIn("add_('A', 'X')", form.errors)

        # Test form submission with invalid data (negative multiply numbers)
        form_data = {
            "multiply_('A', 'X')": -1.3,
            "add_('A', 'X')": "",
            "multiply_('B', 'Y')": "",
            "add_('B', 'Y')": 0.9,
            "multiply_('C', 'Z')": "",
            "add_('C', 'Z')": "",
        }

        form = DynamicRateForm(
            data=form_data, dataframe=self.dataframe, initial_data=self.initial_data
        )

        # Check if the form is invalid due to negative multiply numbers
        self.assertFalse(form.is_valid())

        # Ensure that the error messages reflect the correct fields
        self.assertIn("multiply_('A', 'X')", form.errors)

    def test_save_function(self):
        # Test the save function to ensure it returns a DataFrame
        form_data = {
            "multiply_('A', 'X')": 1.3,
            "add_('A', 'X')": "",
            "multiply_('B', 'Y')": "",
            "add_('B', 'Y')": 0.9,
            "multiply_('C', 'Z')": "",
            "add_('C', 'Z')": "",
        }

        form = DynamicRateForm(
            data=form_data, dataframe=self.dataframe, initial_data=self.initial_data
        )
        self.assertTrue(form.is_valid())  # Ensure form is valid before saving

        result_df = form.save()

        # Ensure that the result is a DataFrame
        self.assertIsInstance(result_df, pd.DataFrame)

        # Check the values in the DataFrame
        self.assertEqual(result_df.loc[("A", "X"), "multiply_value"], 1.3)
        self.assertEqual(result_df.loc[("B", "Y"), "add_value"], 0.9)

        # Assert that 'C', 'Z' does not exist in the result DataFrame
        self.assertNotIn(("C", "Z"), result_df.index)
