from datetime import date

import pandas as pd
from dateutil.relativedelta import relativedelta

from cs_demand_model import DemandModellingDataContainer
from cs_demand_model.config import Config
from cs_demand_model.datastore import fs_datastore
from demand_model import build_prediction_model
from typing import Optional


def predict(
    source: str,
    start: Optional[date] = None,
    end: Optional[date] = None,
    prediction_date: Optional[date] = None,
) -> pd.DataFrame:
    """
    Analyses source between start and end, and then predicts the population at prediction_date.
    """

    datastore = fs_datastore(source)
    config = Config()
    DemandModellingDataContainer(datastore, Config())
    dc = DemandModellingDataContainer(datastore, config)

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
    predictor = build_prediction_model(
        df=dc.to_model,
        daily_entrants=dc.daily_entrants(start, end),
        reference_start=start,
        reference_end=end,
        rate_adjustment=dc.ageing_out,
        external_bin_identifier=tuple(),
    )
    prediction_days = (prediction_date - end).days
    predicted_pop = predictor.predict(prediction_days, progress=True)

    return predicted_pop
