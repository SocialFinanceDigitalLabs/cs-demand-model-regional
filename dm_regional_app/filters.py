import django_filters
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django.contrib.auth import get_user_model

from .models import SavedScenario

User = get_user_model()


class SavedScenarioFilter(django_filters.FilterSet):
    user = django_filters.ModelChoiceFilter(queryset=User.objects.none())

    class Meta:
        model = SavedScenario
        fields = ["user"]

    def __init__(self, *args, **kwargs):
        queryset = kwargs.pop("queryset")
        super().__init__(*args, **kwargs)

        # Dynamically set the queryset for the 'user' filter
        self.filters["user"].queryset = self.get_user_choices(queryset)

    def get_user_choices(self, queryset):
        # Ensure this returns a queryset of User instances
        user_ids = queryset.values_list("user_id", flat=True).distinct()
        return User.objects.filter(id__in=user_ids)

    @property
    def form(self):
        form = super().form
        form.helper = FormHelper()
        form.helper.form_method = "get"
        form.helper.form_class = "form-inline"  # Or any other Bootstrap form class
        form.helper.form_show_labels = False  # Labels inside inputs
        form.helper.add_input(Submit("filter", "Filter", css_class="btn-primary"))
        return form
