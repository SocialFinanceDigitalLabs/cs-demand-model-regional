from django.contrib.auth import get_user_model
from django.db import models

from dm_regional_app.utils import DateAwareJSONDecoder, SeriesAwareJSONEncoder

User = get_user_model()


class AbstractScenario(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    historic_filters = models.JSONField(
        encoder=SeriesAwareJSONEncoder, decoder=DateAwareJSONDecoder
    )
    prediction_parameters = models.JSONField(
        encoder=SeriesAwareJSONEncoder, decoder=DateAwareJSONDecoder
    )
    adjusted_rates = models.JSONField(
        encoder=SeriesAwareJSONEncoder, decoder=DateAwareJSONDecoder, null=True
    )
    adjusted_numbers = models.JSONField(
        encoder=SeriesAwareJSONEncoder, decoder=DateAwareJSONDecoder, null=True
    )
    historic_stock = models.JSONField(
        encoder=SeriesAwareJSONEncoder, decoder=DateAwareJSONDecoder
    )
    adjusted_costs = models.JSONField(
        encoder=SeriesAwareJSONEncoder, decoder=DateAwareJSONDecoder, null=True
    )
    adjusted_proportions = models.JSONField(
        encoder=SeriesAwareJSONEncoder, decoder=DateAwareJSONDecoder, null=True
    )
    inflation_parameters = models.JSONField(
        encoder=SeriesAwareJSONEncoder, decoder=DateAwareJSONDecoder, null=True
    )

    class Meta:
        # if a model is abstract, it will not actually create a database table - just the non-abstract models that inherit this one will.
        abstract = True


class SavedScenario(AbstractScenario):
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.name


class SessionScenario(AbstractScenario):
    # optional foreign key to saved scenario - so that we can update it when the user is done navigating between pages
    saved_scenario = models.ForeignKey(
        SavedScenario, null=True, on_delete=models.CASCADE
    )


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    show_filtering_instructions = models.BooleanField(default=True)
    la = models.CharField(max_length=100, null=True, blank=True)
    show_rate_adjustment_instructions = models.BooleanField(default=True)


class DataSource(models.Model):
    uploaded = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
