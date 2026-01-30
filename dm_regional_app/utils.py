import ast
import json
from datetime import date, datetime

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from ssda903.config import AgeBrackets, PlacementCategories


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
        # Check for Series
        if "__type__" in obj and obj["__type__"] == "pd.Series":
            if obj.get("is_multiindex") == True:
                index = pd.MultiIndex.from_tuples(
                    obj["index"], names=obj.get("index_names")
                )
            else:
                index = obj["index"]
            return pd.Series(obj["data"], index=index)

        # Check for DataFrame
        if "__type__" in obj and obj["__type__"] == "pd.DataFrame":
            if obj.get("is_multiindex") == True:
                index = pd.MultiIndex.from_tuples(
                    obj["index"], names=obj.get("index_names")
                )
                return pd.DataFrame(obj["data"], columns=obj["columns"], index=index)
            else:
                return pd.DataFrame(
                    obj["data"], columns=obj["columns"], index=obj["index"]
                )

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
                index_names = obj.index.names  # Get index names

            # Transform NaN to None only when necessary
            records = []
            for record in obj.to_dict(orient="records"):
                transformed_record = {
                    key: (value if pd.notnull(value) else None)
                    for key, value in record.items()
                }
                records.append(transformed_record)
            columns = obj.columns.tolist()  # Get column names

            output = {
                "__type__": "pd.DataFrame",
                "data": records,
                "columns": columns,
                "index": index,
                "index_names": index_names,
                "is_multiindex": isinstance(obj.index, pd.MultiIndex),
            }

            return output

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


def combine_form_data_with_existing_rates(form_data, saved_data):
    """
    This function takes the form data from DynamicRateForm and rate or number adjustments which have been previously saved
    It will take row data from the form where indices match
    It will retain all other row data from the form and saved data
    """

    # start new data dataframe
    new_data = saved_data.copy()

    # for rows where both form_data and saved_data have the same index
    for idx in form_data.index.intersection(saved_data.index):
        # replace saved data with new data
        new_data.loc[idx] = form_data.loc[idx]

    # Select unmatched rows from form_data that are not in saved_data
    unmatched_form_data = form_data[~form_data.index.isin(saved_data.index)]

    # Concatenate the unmatched form_data to new_data
    combined_data = pd.concat([new_data, unmatched_form_data])

    return combined_data


def remove_age_transitions(df):
    """
    Used to remove age transitions from transitions rate table
    """
    df["from_ages"] = df["from"].str.split("-").str[0]
    df["to_ages"] = df["to"].str.split("-").str[0]

    df = df[df["from_ages"] == df["to_ages"]]

    df = df.drop(columns=["from_ages", "to_ages"])

    return df


def rate_table_sort(df, bin_col, transition=False):
    """
    Sorts entry, exit, and transition rate tables by age and placement as
    a standard sort_values sorts lexicographically, putting 10 before 5.

    Transition rate tables need to be sorted on 'From' and 'To' in order
    to maintain sorting across tables and columns.
    """
    # Retrieve an ordered list of the members of each relevant Enum
    age_list = [a.value.label for a in AgeBrackets._members_by_index()]
    place_list = [a.value.label for a in PlacementCategories._members_by_index()]

    # Making age and placement columns for sorting
    df["split"] = df[bin_col].str.split(" - ")
    df["age_bin"] = df["split"].str[0]
    df["age_bin"] = pd.Categorical(df["age_bin"], categories=age_list, ordered=True)
    df["start_place"] = df["split"].str[-1]
    df["start_place"] = pd.Categorical(
        df["start_place"], categories=place_list, ordered=True
    )

    # Sorts entry and exit rate tables by age then placement
    if transition == False:
        df.sort_values(["age_bin", "start_place"], inplace=True)
        df.drop(columns=["split", "age_bin", "start_place"], inplace=True)

    # Sorts transition rate table by age and placement, then age and placement where
    # children end up
    elif transition:
        df["to_split"] = df["To"].str.split(" - ")
        df["end_age_bin"] = df["to_split"].str[0]
        df["end_age_bin"] = pd.Categorical(
            df["end_age_bin"], categories=age_list, ordered=True
        )
        df["end_place"] = df["to_split"].str[-1]
        df["end_place"] = pd.Categorical(
            df["end_place"], categories=place_list, ordered=True
        )

        df.sort_values(
            ["age_bin", "start_place", "end_age_bin", "end_place"],
            inplace=True,
        )
        df.drop(
            columns=[
                "split",
                "age_bin",
                "start_place",
                "to_split",
                "end_age_bin",
                "end_place",
            ],
            inplace=True,
        )

    return df


def care_type_organiser(df: pd.DataFrame, data_type: str, input_col: str) -> dict:
    """
    Takes a dataframe of a population over time and splits it into a dictionary of dataframes based on the categories in an enum
    """
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


def apply_variances(forecast_by_type: dict, ci_by_type: dict) -> dict:
    """
    Takes a dictionary of forecast populations and a dictionary of variances, both split by the same categories defined by an enum e.g. placement type
    Outputs two new series in the variances dictionary, one each for upper/lower CI
    Upper and lower CI uses 2 x standard deviation - would be good to parameterise this in future!
    """
    care_types = [e.value.label for e in PlacementCategories]
    care_types.append("Total")
    care_types.remove("Not in care")

    for care_type in care_types:
        # square root of variance gives standard deviation
        # currently multiplying by 2 (should really parameterise this)
        ci_by_type[care_type]["upper"] = forecast_by_type[care_type][
            "pop_size"
        ] + 2 * np.sqrt(ci_by_type[care_type]["variance"])
        ci_by_type[care_type]["lower"] = forecast_by_type[care_type][
            "pop_size"
        ] - 2 * np.sqrt(ci_by_type[care_type]["variance"])

    return ci_by_type


def add_traces(fig: go.Figure, traces_list: list) -> go.Figure:
    """
    Adds list of one or more populations (e.g. historic data, base forecast, adjusted forecast) to graph, with each population split by placement categories
    """
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
        for care_dict in traces_list:
            fig.add_trace(
                go.Scatter(
                    x=care_dict[care_type]["date"],
                    y=care_dict[care_type]["pop_size"],
                    name=f"{care_type} ({care_dict['type']})",
                    legendgroup=f"{care_type} ({care_dict['type']})",
                    line=dict(color=colour, width=1.5, dash=care_dict["dash"]),
                )
            )

    return fig


def add_ci_traces(fig: go.Figure, ci_traces_list: list) -> go.Figure:
    """
    Adds confidence interval lines to a plotly graph using data from a dictionary of dataframes split by an enum of placement categories
    """
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
        for ci_dict in ci_traces_list:
            # Add lower bounds for confidence intervals.
            fig.add_trace(
                go.Scatter(
                    x=ci_dict[care_type]["date"],
                    y=ci_dict[care_type]["lower"],
                    line_color="rgba(255,255,255,0)",
                    legendgroup=f"{ci_dict['type']} {care_type}",
                    showlegend=False,
                    hoverinfo="skip",
                )
            )

            # Add upper bounds for confidence intervals.
            fig.add_trace(
                go.Scatter(
                    x=ci_dict[care_type]["date"],
                    y=ci_dict[care_type]["upper"],
                    fill="tonexty",
                    fillcolor=colour,
                    line_color="rgba(255,255,255,0)",
                    legendgroup=f"{ci_dict['type']} {care_type}",
                    showlegend=False,
                    hoverinfo="skip",
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


def weekly_care_type_dfs(
    df,
    *,
    value_col: str,
    round_int: bool = False,
):
    df = df.copy()
    df.index = pd.to_datetime(df.index)

    weekly = df.resample("W").first()

    if round_int:
        weekly = weekly.round().astype(int)

    out = weekly.unstack().reset_index()
    out.columns = ["bin", "date", value_col]

    return care_type_organiser(out, value_col, "bin")
