from bootstrap_datepicker_plus.widgets import DatePickerInput
from django import forms


class PredictFilter(forms.Form):
    start_date = forms.DateField(
        widget=DatePickerInput(),
        label="Start Date",
        required=True,
    )
    end_date = forms.DateField(
        widget=DatePickerInput(range_from="start_date"),
        label="End Date",
        required=True,
    )
