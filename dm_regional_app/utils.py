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
            if obj.get("is_multiindex") == True:
                index = pd.MultiIndex.from_tuples(
                    obj["index"], names=obj.get("index_names")
                )
            else:
                index = obj["index"]
            return pd.Series(obj["data"], index=index)

        # Check for DataFrame
        if "__type__" in obj and obj["__type__"] == "pd.DataFrame":
            print("saved", obj.get("is_multiindex"))
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
            print("is multi index", isinstance(obj.index, pd.MultiIndex))

            output = {
                "__type__": "pd.DataFrame",
                "data": records,
                "columns": columns,
                "index": index,
                "index_names": index_names,
                "is_multiindex": isinstance(obj.index, pd.MultiIndex),
            }
            print(output)

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
