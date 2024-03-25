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

from ssda903 import (
    Config,
    DemandModellingDataContainer,
    PopulationStats,
    StorageDataStore,
)

User = get_user_model()


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        datastore = StorageDataStore(default_storage, settings.DATA_SOURCE)
        config = Config()
        dc = DemandModellingDataContainer(datastore, config)

        print(dc.enriched_view)
