import ast
import json
from datetime import date, datetime

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

    def parse_object(self, obj):
        obj = self.parse_dates(obj)
        if "__type__" in obj and obj["__type__"] == "pd.Series":
            if all(isinstance(i, list) for i in obj["index"]):
                index = pd.MultiIndex.from_tuples(obj["index"])
            else:
                index = obj["index"]
            return pd.Series(obj["data"], index=index)
        return obj


class SeriesAwareJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        # Check if the Series has a MultiIndex
        if isinstance(obj, pd.Series):
            # Check if the Series has a MultiIndex
            if isinstance(obj.index, pd.MultiIndex):
                index = obj.index.tolist()
            else:
                index = obj.index.tolist()
            return {"__type__": "pd.Series", "data": obj.tolist(), "index": index}
        if isinstance(obj, date):
            return obj.isoformat()
        # Let the base class default method raise the TypeError
        return super().default(obj)


def str_to_tuple(string):
    return ast.literal_eval(string)
