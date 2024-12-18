import pandas as pd
from bootstrap_datepicker_plus.widgets import DatePickerInput
from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, Column, Field, Layout, Row, Submit
from django import forms
from django.core.validators import FileExtensionValidator
from django_select2 import forms as s2forms

from dm_regional_app.models import SavedScenario
from dm_regional_app.utils import str_to_tuple


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
        reference_date_min = kwargs.pop("reference_date_min", None)
        reference_date_max = kwargs.pop("reference_date_max", None)

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
    ethnicity = forms.MultipleChoiceField(
        widget=s2forms.Select2MultipleWidget,
        label="Ethnicity",
        required=False,
        choices=[],
    )
    sex = forms.ChoiceField(
        label="Sex",
        required=False,
        choices=[("all", "All"), (1, "Male"), (2, "Female")],
        initial="all",
    )
    uasc = forms.ChoiceField(
        label="UASC",
        required=False,
        choices=[("all", "All"), (True, "UASC only"), (False, "Exclude UASC")],
        initial="all",
    )

    def __init__(self, *args, **kwargs):
        la_choices = kwargs.pop("la")
        ethnicity_choices = kwargs.pop("ethnicity")

        super().__init__(*args, **kwargs)
        self.fields["la"].choices = [(la, la) for la in la_choices]
        self.fields["ethnicity"].choices = [
            (ethnicity, ethnicity) for ethnicity in ethnicity_choices
        ]

        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column("la", css_class="form-group col-md-3 mb-0"),
                Column("ethnicity", css_class="form-group col-md-3 mb-0"),
                Column("sex", css_class="form-group col-md-3 mb-0"),
                Column("uasc", css_class="form-group col-md-3 mb-0"),
                css_class="form-row",
            ),
            Submit("submit", "Filter"),
        )


class DynamicForm(forms.Form):
    def __init__(self, *args, **kwargs):
        self.dataframe = kwargs.pop("dataframe", None)
        initial_data = kwargs.pop("initial_data", pd.Series)

        super(DynamicForm, self).__init__(*args, **kwargs)
        self.initialize_fields(initial_data)

    def initialize_fields(self, initial_data):
        # adjusted rates will be None if user has not changed these before, so check
        if initial_data is not None:
            for index in self.dataframe.index:
                field_name = str(index)
                initial_value = None

                # Attempt to get the initial value using the multiindex
                try:
                    initial_value = initial_data.loc[index]
                except KeyError:
                    initial_value = None

                self.fields[field_name] = forms.FloatField(
                    required=False, initial=initial_value
                )
        else:
            for index in self.dataframe.index:
                field_name = str(index)
                initial_value = None
                self.fields[field_name] = forms.FloatField(
                    required=False, initial=initial_value
                )

    def clean(self):
        cleaned_data = super().clean()
        negative_numbers = []

        for field_name in self.fields:
            value = cleaned_data.get(field_name)
            if value is not None and value < 0:
                negative_numbers.append(field_name)
                self.add_error(field_name, "Negative numbers are not allowed!")

        if negative_numbers:
            raise forms.ValidationError(
                "Form not saved, negative numbers cannot be entered."
            )

    def save(self):
        transition = []
        transition_rate = []
        for field_name, value in self.cleaned_data.items():
            if value:
                transition.append(field_name)
                transition_rate.append(value)

        data = pd.DataFrame(
            {
                "transition": transition,
                "adjusted_rate": transition_rate,
            }
        )
        data["transition"] = data["transition"].apply(str_to_tuple)
        data = data.set_index("transition")

        # if index is tuple, convert to a MultiIndex
        if all(isinstance(idx, tuple) for idx in data.index):
            data.index = pd.MultiIndex.from_tuples(data.index, names=["from", "to"])
        # convert dataframe to series

        data = pd.Series(data["adjusted_rate"].values, index=data.index)

        return data


class InflationForm(forms.Form):
    # Boolean field with radio buttons
    inflation = forms.BooleanField(
        label="Include inflation?",
        required=False,
    )

    # Float field for inflation rate
    inflation_rate = forms.FloatField(
        label="Inflation rate (%)",
        min_value=0.0,
        max_value=100.0,
        required=False,
    )

    def clean_inflation_rate(self):
        rate = self.cleaned_data.get("inflation_rate")
        if rate is not None:
            rate = rate / 100.0  # Convert percentage to decimal
        return rate

    def __init__(self, *args, **kwargs):
        initial = kwargs.get("initial", {})
        if "inflation_rate" in initial and initial["inflation_rate"] is not None:
            initial["inflation_rate"] = (
                initial["inflation_rate"] * 100
            )  # Convert decimal to percentage for display
        kwargs["initial"] = initial
        super(InflationForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.form_show_labels = False
        self.helper.layout = Layout(
            Row(
                Column(
                    HTML(
                        '<label for="id_inflation" class="control-label">Include inflation?</label>'
                    ),
                    css_class="form-group col-md-5 mb-0",
                ),
                Column(
                    Field("inflation", css_class="form-control"),
                    css_class="form-group col-md-4 mb-0",
                ),
                Column(
                    Submit("submit", "Apply", css_class="btn btn-primary align-right"),
                    css_class="form-group col-auto align-right",
                ),
                css_class="form-row",
            ),
            Row(
                Column(
                    HTML(
                        '<label for="id_inflation_rate" class="control-label">Inflation Rate (%)</label>'
                    ),
                    css_class="form-group col-md-5 mb-0",
                ),
                Column(
                    Field("inflation_rate", css_class="form-control"),
                    css_class="form-group col-md-3 mb-0",
                ),
                css_class="form-row",
            ),
        )


class SavedScenarioForm(forms.ModelForm):
    name = forms.CharField(
        widget=forms.TextInput(attrs={"maxlength": 100}),
        max_length=400,
        required=True,
        label="Name",
    )
    description = forms.CharField(
        widget=forms.TextInput(attrs={"maxlength": 400}),
        max_length=400,
        required=False,
        label="Description",
    )

    class Meta:
        model = SavedScenario
        fields = ["name", "description"]

    def __init__(self, *args, **kwargs):
        super(SavedScenarioForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.layout = Layout(
            Field("name", css_class="form-control"),
            Field("description", css_class="form-control"),
        )


class DataSourceUploadForm(forms.Form):
    episodes = forms.FileField(
        validators=[
            FileExtensionValidator(
                allowed_extensions=["csv"], message="File must have extension .csv"
            )
        ]
    )
    header = forms.FileField(
        validators=[
            FileExtensionValidator(
                allowed_extensions=["csv"], message="File must have extension .csv"
            )
        ]
    )
    uasc = forms.FileField(
        label="UASC",
        validators=[
            FileExtensionValidator(
                allowed_extensions=["csv"], message="File must have extension .csv"
            )
        ],
    )
