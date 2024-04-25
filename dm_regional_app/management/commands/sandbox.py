from datetime import date
from typing import Optional

import pandas as pd
from dateutil.relativedelta import relativedelta
from demand_model import MultinomialPredictor
from demand_model.multinomial.predictor import Prediction
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand
from django.shortcuts import get_object_or_404

from dm_regional_app.models import SavedScenario, SessionScenario
from ssda903 import (
    Config,
    DemandModellingDataContainer,
    PopulationStats,
    StorageDataStore,
)

User = get_user_model()


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        """thing = User.objects.all()
        for t in thing:
            print(t.profile.la)"""
        datastore = StorageDataStore(default_storage, settings.DATA_SOURCE)
        config = Config()
        dc = DemandModellingDataContainer(datastore, config)
        pop = PopulationStats(dc.enriched_view, config)

        data = dc.enriched_view
        # print(data.loc[data.UASC == True])

        # print(pop.stock)
        # print(dc.enriched_view)
        session_scenario = get_object_or_404(SessionScenario, pk=1)
        print(session_scenario.historic_filters)
        print(type(session_scenario.historic_filters))

        """
        
        for key, value in session_scenario.historic_filters.items():
            print(key, value)
"""
