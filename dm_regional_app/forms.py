from django import forms
    

class PredictFilter(forms.Form):
    start_date = forms.DateField(
        widget=forms.widgets.DateInput(attrs={'type': 'date'}),
        label='Start Date',
        required=True,
    )
    end_date = forms.DateField(
        widget=forms.widgets.DateInput(attrs={'type': 'date'}),
        label='End Date',
        required=True,
    )
