import ast
import json
from datetime import date, datetime

import pandas as pd
import plotly.graph_objects as go

from ssda903.config import PlacementCategories


def apply_filters(data: pd.DataFrame, filters: dict):
    if filters["la"] != []:
        loc = data.LA.astype(str).isin(filters["la"])
        data = data.loc[loc]

    if filters["ethnicity"] != []:
        loc = data.ethnicity.astype(str).isin(filters["ethnicity"])
        data = data.loc[loc]

    if filters["sex"] == "1":
        data = data.loc[data.SEX == 1.0]
    elif filters["sex"] == "2":
        data = data.loc[data.SEX == 2.0]

    if filters["uasc"] == "True":
        data = data.loc[data.UASC == True]
    elif filters["uasc"] == "False":
        data = data.loc[data.UASC == False]

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
    df["from_ages"] = df["from"].str.split("-").str[0]
    df["to_ages"] = df["to"].str.split("-").str[0]

    df = df[df["from_ages"] == df["to_ages"]]

    df.drop(columns=["from_ages", "to_ages"], inplace=True)

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

    # Sorts entry and exit rate tables by age then placement
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

def care_type_organiser(df, data_type, input_col):
    # Used on forecast, historic, and variance data to organise by care types,
    # outpouts to a dictionary of dfs.
    care_types = [e.value.label for e in PlacementCategories]
    care_types.append("Total")
    care_types.remove("Not in care")

    care_type_dict = {}

    for care_type in care_types:
        if care_type == "Total":
            care_type_df = df[
                df[input_col].apply(lambda x: "Not in care" in x) == False
            ]
        else:
            care_type_df = df[df[input_col].str.contains(care_type)]

        care_type_df = (
            care_type_df[["date", data_type]].groupby("date").sum().reset_index()
        )
        care_type_df["date"] = pd.to_datetime(care_type_df["date"]).dt.date

        care_type_dict[care_type] = care_type_df

    return care_type_dict


def apply_variances(care_by_type, ci_by_type):
    # Applies pre-calculated variance make the df needed for plotting
    # confidence intervals.
    care_types = [e.value.label for e in PlacementCategories]
    care_types.append("Total")
    care_types.remove("Not in care")

    for care_type in care_types:
        ci_by_type[care_type]["upper"] = (
            care_by_type[care_type]["forecast"] + ci_by_type[care_type]["variance"]
        )
        ci_by_type[care_type]["lower"] = (
            care_by_type[care_type]["forecast"] - ci_by_type[care_type]["variance"]
        )

    return ci_by_type


def add_traces(dfs_forecast, dfs_historic, fig):
    care_types = [e.value.label for e in PlacementCategories]
    care_types.append("Total")
    care_types.remove("Not in care")

    colours = {
        "purple": "rgba(159, 0, 160, 1)",
        "green": "rgba(0, 160, 36, 1)",
        "blue": "rgba(6, 0, 160, 1)",
        "red": "rgba(241, 0, 0, 1)",
        "black": "rgba(0, 0, 0, 1)",
    }

    for care_type, colour in zip(care_types, colours.values()):
        if dfs_forecast:
            # Add forecast data.
            fig.add_trace(
                go.Scatter(
                    x=dfs_forecast[care_type]["date"],
                    y=dfs_forecast[care_type]["forecast"],
                    name=f"Forecast ({care_type})",
                    line=dict(color=colour, width=1.5),
                )
            )

        # Add historic data.
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
    care_types = [e.value.label for e in PlacementCategories]
    care_types.append("Total")
    care_types.remove("Not in care")

    colours = {
        "purple": "rgba(159, 0, 160, 0.2)",
        "green": "rgba(0, 160, 36, 0.2)",
        "blue": "rgba(6, 0, 160, 0.2)",
        "red": "rgba(241, 0, 0, 0.2)",
        "black": "rgba(0, 0, 0, 0.2)",
    }

    for care_type, colour in zip(care_types, colours.values()):
        # Add lower bounds for confidence intervals.
        fig.add_trace(
            go.Scatter(
                x=df[care_type]["date"],
                y=df[care_type]["lower"],
                line_color="rgba(255,255,255,0)",
                name=f"Confidence interval ({care_type})",
                showlegend=False,
            )
        )

        # Add upper bounds for confidence intervals.
        fig.add_trace(
            go.Scatter(
                x=df[care_type]["date"],
                y=df[care_type]["upper"],
                fill="tonexty",
                fillcolor=colour,
                line_color="rgba(255,255,255,0)",
                name=f"Confidence interval ({care_type})",
                showlegend=True,
            )
        )

    return fig

  
def save_data_if_not_empty(session_scenario, data, attribute_name):
    """
    Checks if series or dataframe is not empty, and saves to attribute of model if not
    """
    if isinstance(data, (pd.DataFrame, pd.Series)) and not data.empty:
        setattr(session_scenario, attribute_name, data)
        session_scenario.save()
