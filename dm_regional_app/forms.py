import pandas as pd
from bootstrap_datepicker_plus.widgets import DatePickerInput
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Column, Layout, Row, Submit
from django import forms
from django_select2 import forms as s2forms


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
    la = forms.MultipleChoiceField(
        widget=s2forms.Select2MultipleWidget,
        label="Local Authority",
        required=False,
        choices=[],
    )
    placement_types = forms.MultipleChoiceField(
        widget=s2forms.Select2MultipleWidget,
        label="Placement Type",
        required=False,
        choices=[],
    )
    age_bins = forms.MultipleChoiceField(
        widget=s2forms.Select2MultipleWidget,
        label="Age",
        required=False,
        choices=[],
    )
    uasc = forms.ChoiceField(
        label="UASC",
        required=False,
        choices=[("all", "All"), (True, "UASC only"), (False, "Exclude UASC")],
        initial="all",
    )

    def __init__(self, *args, **kwargs):
        la_choices = kwargs.pop("la_choices")
        placement_type_choices = kwargs.pop("placement_type_choices")
        age_bin_choices = kwargs.pop("age_bin_choices")

        super().__init__(*args, **kwargs)
        self.fields["la"].choices = [(la, la) for la in la_choices]
        self.fields["placement_types"].choices = [
            (placement_type, placement_type)
            for placement_type in placement_type_choices
        ]
        self.fields["age_bins"].choices = [
            (age_bin, age_bin) for age_bin in age_bin_choices
        ]

        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column("start_date", css_class="form-group col-md-3 mb-0"),
                Column("end_date", css_class="form-group col-md-3 mb-0"),
                css_class="form-row",
            ),
            Row(
                Column("la", css_class="form-group col-md-3 mb-0"),
                Column("placement_types", css_class="form-group col-md-3 mb-0"),
                Column("age_bins", css_class="form-group col-md-3 mb-0"),
                Column("uasc", css_class="form-group col-md-3 mb-0"),
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
        if self.cleaned_data["la"] != []:
            loc = data.LA.astype(str).isin(self.cleaned_data["la"])
            data = data.loc[loc]
        return data

    def filter_by_placement_type(self, data: pd.DataFrame):
        if self.cleaned_data["placement_types"] != []:
            loc = data.placement_type.astype(str).isin(
                self.cleaned_data["placement_types"]
            )
            data = data.loc[loc]
        return data

    def filter_by_age_bin(self, data: pd.DataFrame):
        if self.cleaned_data["age_bins"] != []:
            loc = data.age_bin.astype(str).isin(self.cleaned_data["age_bins"])
            data = data.loc[loc]
        return data

    def filter_by_uasc(self, data: pd.DataFrame):
        if self.cleaned_data["uasc"] == "True":
            data = data.loc[data.UASC == True]
        elif self.cleaned_data["uasc"] == "False":
            data = data.loc[data.UASC == True]
        return data

    def apply_filters(self, data: pd.DataFrame):
        data = self.filter_by_start_date(data)
        data = self.filter_by_end_date(data)
        data = self.filter_by_la(data)
        data = self.filter_by_placement_type(data)
        data = self.filter_by_age_bin(data)
        data = self.filter_by_uasc(data)
        return data
