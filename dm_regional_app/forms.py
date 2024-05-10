from bootstrap_datepicker_plus.widgets import DatePickerInput
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Column, Layout, Row, Submit
from django import forms
from django_select2 import forms as s2forms


class PredictFilter(forms.Form):
    reference_start_date = forms.DateField(
        label="Reference Start Date",
        required=True,
        help_text="Select the period you would like the model to reference",
    )
    reference_end_date = forms.DateField(
        label="Reference End Date",
        required=True,
    )
    prediction_start_date = forms.DateField(
        widget=DatePickerInput(),
        label="Prediction Start Date",
        required=False,
        help_text="Select the future date-range you want to apply your forecast to",
    )
    prediction_end_date = forms.DateField(
        widget=DatePickerInput(),
        label="Prediction End Date",
        required=False,
    )

    def __init__(self, *args, **kwargs):
        reference_date_min = kwargs.pop("start_date", None)
        reference_date_max = kwargs.pop("end_date", None)

        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column("reference_start_date", css_class="form-group col-md-3 mb-0"),
                Column("reference_end_date", css_class="form-group col-md-3 mb-0"),
                css_class="form-row",
            ),
            Row(
                Column("prediction_start_date", css_class="form-group col-md-3 mb-0"),
                Column("prediction_end_date", css_class="form-group col-md-3 mb-0"),
                css_class="form-row",
            ),
            Submit("submit", "Run model"),
        )

        self.fields["reference_start_date"].widget = DatePickerInput(
            options={"minDate": reference_date_min, "maxDate": reference_date_max}
        )

        self.fields["reference_end_date"].widget = DatePickerInput(
            options={"minDate": reference_date_min, "maxDate": reference_date_max}
        )

    def clean(self):
        cleaned_data = super().clean()
        reference_start_date = cleaned_data.get("reference_start_date")
        reference_end_date = cleaned_data.get("reference_end_date")
        prediction_start_date = cleaned_data.get("prediction_start_date")
        prediction_end_date = cleaned_data.get("prediction_end_date")

        if reference_start_date and reference_end_date:
            if reference_start_date >= reference_end_date:
                raise forms.ValidationError(
                    "Reference start date must be before reference end date."
                )

        if prediction_start_date and prediction_end_date:
            if prediction_start_date >= prediction_end_date:
                raise forms.ValidationError(
                    "Prediction start date must be before prediction end date."
                )


class HistoricDataFilter(forms.Form):
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
        la_choices = kwargs.pop("la")
        placement_type_choices = kwargs.pop("placement_types")
        age_bin_choices = kwargs.pop("age_bins")

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
                Column("la", css_class="form-group col-md-3 mb-0"),
                Column("placement_types", css_class="form-group col-md-3 mb-0"),
                Column("age_bins", css_class="form-group col-md-3 mb-0"),
                Column("uasc", css_class="form-group col-md-3 mb-0"),
                css_class="form-row",
            ),
            Submit("submit", "Filter"),
        )
