import pandas as pd
from bootstrap_datepicker_plus.widgets import DatePickerInput
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Column, Layout, Row, Submit
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


class HistoricDataFilter(forms.Form):
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
    la = forms.ChoiceField(label="Local Authority", required=False, choices=[])
    placement_types = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple,
        label="Placement Type",
        required=False,
        choices=[],
    )

    def __init__(self, *args, **kwargs):
        la_choices = kwargs.pop("la_choices")
        placement_type_choices = kwargs.pop("placement_type_choices")

        super().__init__(*args, **kwargs)
        self.fields["la"].choices = [("all", "All")] + [(la, la) for la in la_choices]
        self.fields["la"].initial = "all"
        self.fields["placement_types"].choices = [
            (placement_type, placement_type)
            for placement_type in placement_type_choices
        ]
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column("start_date", css_class="form-group col-md-6 mb-0"),
                Column("end_date", css_class="form-group col-md-6 mb-0"),
                css_class="form-row",
            ),
            Row(
                Column("la", css_class="form-group col-md-6 mb-0"),
                Column("placement_types", css_class="form-group col-md-4 mb-0"),
                css_class="form-row",
            ),
            Submit("submit", "Filter"),
        )

    def filter_by_start_date(self, data: pd.DataFrame):
        data = data.loc[data.DECOM.dt.date >= self.cleaned_data["start_date"]]
        return data

    def filter_by_end_date(self, data: pd.DataFrame):
        data = data.loc[data.DEC.dt.date <= self.cleaned_data["end_date"]]
        return data

    def filter_by_la(self, data: pd.DataFrame):
        if self.cleaned_data["la"] != "all":
            data = data.loc[data.LA == self.cleaned_data["la"]]
        return data

    def filter_by_placement_type(self, data: pd.DataFrame):
        if self.cleaned_data["placement_types"] != []:
            loc = data.placement_type.astype(str).isin(
                self.cleaned_data["placement_types"]
            )
            data = data.loc[loc]
        return data

    def apply_filters(self, data: pd.DataFrame):
        data = self.filter_by_start_date(data)
        data = self.filter_by_end_date(data)
        data = self.filter_by_la(data)
        data = self.filter_by_placement_type(data)
        return data
