from datetime import date

import pandas as pd
from dateutil.relativedelta import relativedelta

from ssda903 import DemandModellingDataContainer, PopulationStats, Config, fs_datastore
from demand_model import MultinomialPredictor
from demand_model.multinomial.predictor import Prediction
from typing import Optional


def predict(
    source: str,
    start: Optional[date] = None,
    end: Optional[date] = None,
    prediction_date: Optional[date] = None,
) -> Prediction:
    """
    Analyses source between start and end, and then predicts the population at prediction_date.
    """

    datastore = fs_datastore(source)
    config = Config()
    dc = DemandModellingDataContainer(datastore, config)
    stats = PopulationStats(dc.enriched_view, config)
    if start is None:
        start = dc.end_date - relativedelta(months=6)

    if end is None:
        end = dc.end_date

    if prediction_date is None:
        prediction_date = end + relativedelta(months=12)
    print(
        f"Running analysis between {start} and {end} "
        f"and predicting to {prediction_date}"
    )
   
    predictor = MultinomialPredictor(
        population=stats.stock_at(end),
        transition_rates=stats.raw_transition_rates(start, end),
        transition_numbers=stats.daily_entrants(start, end),
        start_date=end,
    )
    prediction_days = (prediction_date - end).days
    prediction = predictor.predict(prediction_days, progress=True)

    return prediction
