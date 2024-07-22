from datetime import date
from decimal import Decimal
from typing import Optional

import pandas as pd
from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand
from django.shortcuts import get_object_or_404

from dm_regional_app.models import SavedScenario, SessionScenario
from ssda903 import DemandModellingDataContainer, PopulationStats, StorageDataStore
from ssda903.config import Costs
from ssda903.costs import forecast_costs
from ssda903.predictor import predict

User = get_user_model()


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        """thing = User.objects.all()
        for t in thing:
            print(t.profile.la)"""
        datastore = StorageDataStore(default_storage, settings.DATA_SOURCE)
        dc = DemandModellingDataContainer(datastore)
        pop = PopulationStats(dc.enriched_view)

        data = dc.enriched_view
        # print(data.columns)

        prediction = predict(
            data=data,
            reference_start_date=dc.start_date,
            reference_end_date=dc.end_date,
        )

        proportion_adjustment = pd.Series(
            {
                "Fostering (Friend/Relative)": 0.45,
                "Fostering (In-house)": 0.35,
                "Fostering (IFA)": 0.4,
                "Residential (In-house)": 0.8,
                "Residential (External)": 0.4,
            }
        )

        cost_adjustment = pd.Series(
            {
                "Fostering (Friend/Relative)": 120,
                "Fostering (In-house)": 160,
                "Residential (In-house)": 900,
            }
        )

        proportion_adjustment = None

        costs = forecast_costs(
            prediction,
            proportion_adjustment=proportion_adjustment,
            cost_adjustment=cost_adjustment,
        )

        scale_factor = (Decimal("1") - Decimal(0.2)) / Decimal(0.4)
        print(scale_factor)

        # print(pop.stock)
        # print(dc.enriched_view)
        # session_scenario = get_object_or_404(SessionScenario, pk=1)
        # print(session_scenario.historic_filters)
        # print(type(session_scenario.historic_filters))

        """
        
        for key, value in session_scenario.historic_filters.items():
            print(key, value)
"""
