from datetime import date
from typing import Optional

import pandas as pd
from dateutil.relativedelta import relativedelta

from ssda903 import PopulationStats
from ssda903.multinomial import MultinomialPredictor, Prediction


def predict(
    stats: PopulationStats,
    reference_start_date: date,
    reference_end_date: date,
    prediction_start_date: Optional[date] = None,
    prediction_end_date: Optional[date] = None,
    rate_adjustment: Optional[pd.DataFrame] = None,
    number_adjustment: Optional[pd.DataFrame] = None,
) -> Prediction:
    """
    Analyses source between start and end, and then predicts the population at prediction_date.
    """
    if prediction_start_date is None:
        prediction_start_date = reference_end_date
    if prediction_end_date is None:
        prediction_end_date = prediction_start_date + relativedelta(months=24)
    print(
        f"Running analysis between {reference_start_date:} and {reference_end_date} "
        f"and predicting from {prediction_start_date} to {prediction_end_date}"
    )

    predictor = MultinomialPredictor(
        population=stats.stock_at(prediction_start_date),
        transition_rates=stats.raw_transition_rates(
            reference_start_date, reference_end_date
        ),
        transition_numbers=stats.daily_entrants(
            reference_start_date, reference_end_date
        ),
        start_date=prediction_start_date,
        rate_adjustment=rate_adjustment,
        number_adjustment=number_adjustment,
    )
    prediction_days = (prediction_end_date - prediction_start_date).days
    prediction = predictor.predict(prediction_days, progress=False)

    return prediction
