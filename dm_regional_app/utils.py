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
        super().__init__(object_hook=self.parse_object, *args, **kwargs)

    def parse_object(self, obj):
        obj = self.parse_dates(obj)
        # Check for Series
        if "__type__" in obj and obj["__type__"] == "pd.Series":
            if obj.get("is_multiindex", False):
                index = pd.MultiIndex.from_tuples(
                    obj["index"], names=obj.get("index_names")
                )
            else:
                index = obj["index"]
            return pd.Series(obj["data"], index=index)

        # Check for DataFrame
        if "__type__" in obj and obj["__type__"] == "pd.DataFrame":
            if obj.get("is_multiindex", False):
                index = pd.MultiIndex.from_tuples(
                    obj["index"], names=obj.get("index_names")
                )
                return pd.DataFrame(obj["data"], columns=obj["columns"], index=index)
            else:
                return pd.DataFrame(obj["data"], columns=obj["columns"])

        return obj

    def parse_dates(self, obj):
        for key, value in obj.items():
            if isinstance(value, str) and "date" in key:
                try:
                    obj[key] = datetime.fromisoformat(value).date()
                except ValueError:
                    pass
        return obj


class SeriesAwareJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, pd.Series):
            # Check if the Series has a MultiIndex
            if isinstance(obj.index, pd.MultiIndex):
                index = [list(tup) for tup in obj.index]
            else:
                index = obj.index.tolist()
            return {
                "__type__": "pd.Series",
                "data": obj.tolist(),
                "index": index,
                "is_multiindex": isinstance(obj.index, pd.MultiIndex),
            }

        if isinstance(obj, pd.DataFrame):
            # Handle MultiIndex DataFrame
            if isinstance(obj.index, pd.MultiIndex):
                index = [
                    list(tup) for tup in obj.index
                ]  # Convert MultiIndex to list of lists
                index_names = obj.index.names  # Get index names
            else:
                index = obj.index.tolist()
                index_names = [None] * len(
                    index
                )  # Create placeholder for non-MultiIndex

            records = obj.to_dict(
                orient="records"
            )  # Convert DataFrame to list of dictionaries (rows)
            columns = obj.columns.tolist()  # Get column names

            return {
                "__type__": "pd.DataFrame",
                "data": records,
                "columns": columns,
                "index": index,
                "index_names": index_names,
                "is_multiindex": isinstance(obj.index, pd.MultiIndex),
            }

        if isinstance(obj, date):
            return obj.isoformat()
        # Let the base class default method raise the TypeError
        return super().default(obj)


def str_to_tuple(string):
    """
    will convert string to a tuple if possible, otherwise will return string
    """
    try:
        return ast.literal_eval(string)
    except Exception:
        return string


def number_format(value):
    if value < 0:
        return f"-£{abs(value):,.2f}"
    else:
        return f"£{value:,.2f}"
