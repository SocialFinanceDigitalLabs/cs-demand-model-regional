import ast
import json
import re
from datetime import date, datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# data for care type functions
care_types = [
    "Total",
    "Fostering",
    "Not in care",
    "Residential",
    "Other",
    "Supported",
]


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


def care_type_organiser(df):
    care_type_dict = {}

    if "forecast" in df.columns:
        data_type = "forecast"
    elif "historic" in df.columns:
        data_type = "historic"
    elif "variance" in df.columns:
        data_type = "variance"

    for care_type in care_types:
        if care_type == "Total":
            care_type_df = df[df["from"].apply(lambda x: "Not in care" in x) == False]
        else:
            care_type_df = df[df["from"].str.contains(care_type)]

        care_type_df = (
            care_type_df[["date", data_type]].groupby("date").sum().reset_index()
        )
        care_type_df["date"] = pd.to_datetime(care_type_df["date"]).dt.date

        care_type_dict[care_type] = care_type_df

    return care_type_dict


def apply_variances(care_by_type, ci_by_type):
    for care_type in care_types:
        ci_by_type[care_type]["upper"] = (
            care_by_type[care_type]["forecast"] + ci_by_type[care_type]["variance"]
        )
        ci_by_type[care_type]["lower"] = (
            care_by_type[care_type]["forecast"] - ci_by_type[care_type]["variance"]
        )

    return ci_by_type


def add_traces(dfs_forecast, dfs_historic, fig):
    # Uses an accessible colour scheme from: https://personal.sron.nl/~pault/
    # Exact RGB codes cause some weirdness with plotly so text colours were used instead.

    colours = [
        "blue",
        "green",
        "yellow",
        "red",
        "purple",
    ]

    care_types.remove("Not in care")
    for care_type, colour in zip(care_types, colours):
        # add forecast data
        fig.add_trace(
            go.Scatter(
                x=dfs_forecast[care_type]["date"],
                y=dfs_forecast[care_type]["forecast"],
                name=f"Forecast ({care_type})",
                line=dict(color=colour, width=1.5),
            )
        )

        # add historic data
        fig.add_trace(
            go.Scatter(
                x=dfs_historic[care_type]["date"],
                y=dfs_historic[care_type]["historic"],
                name=f"Historic data ({care_type})",
                line=dict(color=colour, width=1.5, dash="dot"),
            )
        )

    return fig


def add_ci_traces(df, fig):
    # care_types.remove('Not in care')
    for care_type in care_types:
        fig.add_trace(
            go.Scatter(
                x=df[care_type]["date"],
                y=df[care_type]["lower"],
                line_color="rgba(255,255,255,0)",
                name=f"Confidence interval ({care_type})",
                showlegend=False,
            )
        )

        fig.add_trace(
            go.Scatter(
                x=df[care_type]["date"],
                y=df[care_type]["upper"],
                fill="tonexty",
                fillcolor="rgba(0,176,246,0.2)",
                line_color="rgba(255,255,255,0)",
                name=f"Confidence interval ({care_type})",
                showlegend=True,
            )
        )

    return fig
