from datetime import date
from typing import Optional

import pandas as pd
from dateutil.relativedelta import relativedelta
from demand_model import MultinomialPredictor
from demand_model.multinomial.predictor import Prediction

from ssda903 import Config, PopulationStats


def predict(
    data: pd.DataFrame,
    start: date,
    end: date,
    prediction_date: Optional[date] = None,
) -> Prediction:
    """
    Analyses source between start and end, and then predicts the population at prediction_date.
    """
    config = Config()
    stats = PopulationStats(data, config)
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
    prediction = predictor.predict(prediction_days, progress=False)

    return prediction
