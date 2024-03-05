from django.core.management.base import BaseCommand
from datetime import date

import pandas as pd
from dateutil.relativedelta import relativedelta

from ssda903 import DemandModellingDataContainer, PopulationStats, Config, fs_datastore
from demand_model import MultinomialPredictor
from demand_model.multinomial.predictor import Prediction
from typing import Optional



class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        datastore = fs_datastore("sample://v1.zip")
        config = Config()
        dc = DemandModellingDataContainer(datastore, config)

        print(dc.enriched_view)

