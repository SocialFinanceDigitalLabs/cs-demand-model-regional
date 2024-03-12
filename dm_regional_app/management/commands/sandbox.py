from datetime import date
from typing import Optional

import pandas as pd
from dateutil.relativedelta import relativedelta
from demand_model import MultinomialPredictor
from demand_model.multinomial.predictor import Prediction
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from ssda903 import Config, DemandModellingDataContainer, PopulationStats, fs_datastore

User = get_user_model()


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        thing = User.objects.all()
        for t in thing:
            print(t.profile.la)

        """datastore = fs_datastore("sample://v1.zip")
        config = Config()
        dc = DemandModellingDataContainer(datastore, config)

        
        print(dc.enriched_view)"""
