import json
from datetime import datetime

import pandas as pd


def apply_filters(data: pd.DataFrame, filters: dict):
    if filters["la"] != []:
        loc = data.LA.astype(str).isin(filters["la"])
        data = data.loc[loc]

    if filters["placement_types"] != []:
        loc = data.placement_type.astype(str).isin(filters["placement_types"])
        data = data.loc[loc]

    if filters["age_bins"] != []:
        loc = data.age_bin.astype(str).isin(filters["age_bins"])
        data = data.loc[loc]

    if filters["uasc"] == "True":
        data = data.loc[data.UASC == True]
    elif filters["uasc"] == "False":
        data = data.loc[data.UASC == True]

    return data


class DateAwareJSONDecoder(json.JSONDecoder):
    def __init__(self, *args, **kwargs):
        super().__init__(object_hook=self.parse_dates, *args, **kwargs)

    def parse_dates(self, obj):
        for key, value in obj.items():
            if isinstance(value, str) and "date" in key:
                try:
                    obj[key] = datetime.fromisoformat(value).date()
                except ValueError:
                    pass
        return obj
