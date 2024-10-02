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
        if "__type__" in obj and obj["__type__"] == "pd.Series":
            if obj.get("is_multiindex", False):
                index = pd.MultiIndex.from_tuples(obj["index"])
            else:
                index = obj["index"]
            return pd.Series(obj["data"], index=index)
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


def remove_age_transitions(df):
    """
    Used to remove age transitions from transitions rate table
    """
    age_up_16 = df["from"].str.contains("10 to 16") & df["to"].str.contains("16 to 18+")
    age_up_10 = df["from"].str.contains("5 to 10") & df["to"].str.contains("10 to 16")

    df = df[~(age_up_16 | age_up_10)]

    df
    return df


def rate_table_sort(df, bin_col, transition=False):
    """
    Sorts entry, exit, and transition rate tables by age and placement as
    a standard sort_values sorts lexicographically, putting 10 befor 5.

    Transition rate tables need to be sorted on 'From' and 'To' in order
    to maintain sorting across tables and columns.
    """
    # Making age and placement columns for sorting
    df["split"] = df[bin_col].str.split(" ")
    df["first_age"] = df["split"].str[0].astype("int")
    df["starting_place"] = df["split"].str[-1]

    # Sorts entry and exit ratre tables by age then placement
    if transition == False:
        df.sort_values(["first_age", "starting_place"], inplace=True)
        df.drop(columns=["first_age", "starting_place", "split"], inplace=True)

    # Sorts transition rate table by age and placement, then age and placement where
    # children end up
    elif transition:
        df["to_split"] = df["To"].str.split(" ")
        df["finishing_age"] = df["to_split"].str[0].astype("int")
        df["finishing_place"] = df["to_split"].str[-1]
        df.sort_values(
            ["first_age", "starting_place", "finishing_age", "finishing_place"],
            inplace=True,
        )
        df.drop(
            columns=[
                "first_age",
                "starting_place",
                "split",
                "finishing_place",
                "to_split",
                "finishing_age",
            ],
            inplace=True,
        )

    return df
