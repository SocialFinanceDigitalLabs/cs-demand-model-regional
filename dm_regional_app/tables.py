import django_tables2 as tables
from django.urls import reverse
from django.utils.html import format_html

from dm_regional_app.models import SavedScenario


class SavedScenarioTable(tables.Table):
    updated_at = tables.DateTimeColumn(format="d/m/Y H:i:s", accessor="updated_at")
    view = tables.Column(empty_values=(), verbose_name="")

    class Meta:
        model = SavedScenario
        template_name = "django_tables2/bootstrap-responsive.html"
        fields = (
            "name",
            "description",
            "user",
            "updated_at",
        )  # Specify the fields you want to display

    def render_view(self, record):
        url = reverse("load_scenario", args=[record.pk])
        return format_html(
            '<a href="{}" class="btn btn-primary">Load scenario</a>', url
        )
