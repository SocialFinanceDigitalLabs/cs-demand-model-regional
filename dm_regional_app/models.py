from django.contrib.auth import get_user_model
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models

from dm_regional_app.utils import DateAwareJSONDecoder

User = get_user_model()


class AbstractScenario(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    historic_filters = models.JSONField(
        encoder=DjangoJSONEncoder, decoder=DateAwareJSONDecoder
    )
    prediction_filters = models.JSONField(
        encoder=DjangoJSONEncoder, decoder=DateAwareJSONDecoder
    )
    prediction_parameters = models.JSONField(
        encoder=DjangoJSONEncoder, decoder=DateAwareJSONDecoder
    )
    historic_stock = models.JSONField(
        encoder=DjangoJSONEncoder, decoder=DateAwareJSONDecoder
    )
    adjusted_costs = models.JSONField(
        encoder=DjangoJSONEncoder, decoder=DateAwareJSONDecoder
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
    show_instructions = models.BooleanField(default=True)
    la = models.CharField(max_length=100, null=True, blank=True)
