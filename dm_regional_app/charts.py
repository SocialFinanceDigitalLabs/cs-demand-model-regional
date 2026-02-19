import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from dm_regional_app.utils import (
    add_ci_traces,
    add_traces,
    apply_variances,
    care_type_organiser,
    rate_table_sort,
    remove_age_transitions,
    weekly_care_type_dfs,
)
from ssda903.config import Costs
from ssda903.costs import CostForecast
from ssda903.multinomial import Prediction
from ssda903.population_stats import PopulationStats


def year_one_costs(df: CostForecast):
    """
    This function takes a CostForecast and filters to only values in the first year, returning a single sum of those values.
    """

    df = df.costs

    # Ensure the index is a DatetimeIndex
    df.index = pd.to_datetime(df.index)

    # Find the first date in the DataFrame index
    first_date = df.index.min()

    # Calculate the end date (one year from the first date)
    end_date = first_date + pd.DateOffset(years=1)

    # Filter the DataFrame
    df = df[(df.index >= first_date) & (df.index < end_date)]

    # Sum all values in the DataFrame, round to 2 decimal places
    total_sum = df.to_numpy().sum().round(2)

    return total_sum


def area_chart_cost(df_historic, prediction: CostForecast):
    df_forecast = prediction.costs
    prediction_start_date = df_forecast.index[0]

    df_historic = df_historic.loc[:prediction_start_date]

    combined_df = pd.concat([df_historic, df_forecast], copy=False)

    combined_df.index = pd.to_datetime(combined_df.index)

    combined_df_weekly = combined_df.resample("W").first()

    fig = px.area(
        combined_df_weekly,
        x=combined_df_weekly.index,
        y=combined_df_weekly.columns,
        labels={"variable": "", "value": "Cost in £", "index": "Date"},
    )

    fig.add_vline(
        x=prediction_start_date,
        line_width=1,
        line_dash="dash",
        line_color="black",
    )

    fig.update_layout(title="Child placement costs")
    fig_html = fig.to_html(full_html=False, include_plotlyjs="cdn")

    return fig_html


def area_chart_population(historic_data: pd.DataFrame, prediction: CostForecast):
    # Forecast
    df_forecast = prediction.proportional_population.round().astype(int)
    df_forecast.index = pd.to_datetime(df_forecast.index)
    weekly_forecast = df_forecast.resample("W").first()

    # Historic
    df_historic = historic_data
    df_historic.index = pd.to_datetime(df_historic.index)
    weekly_historic = df_historic.resample("W").first()

    # Only keep historic dates before forecast starts
    prediction_start_date = weekly_forecast.index[0]
    weekly_historic = weekly_historic.loc[:prediction_start_date]

    # Combine
    combined_df = pd.concat([weekly_historic, weekly_forecast], copy=False)

    # Plot (wide-form)
    fig = px.area(
        combined_df,
        x=combined_df.index,
        y=combined_df.columns,
        labels={"variable": "", "value": "Population", "index": "Date"},
    )

    fig.add_vline(
        x=prediction_start_date, line_width=1, line_dash="dash", line_color="black"
    )

    fig.update_layout(title="Child placement numbers")

    # Fast HTML generation with CDN
    fig_html = fig.to_html(full_html=False, include_plotlyjs="cdn")

    return fig_html


def placement_proportion_table(historic_proportions, forecast_proportion: CostForecast):
    categories = {item.value.label: item.value.category.label for item in Costs}

    forecast_proportion = forecast_proportion.proportions.sort_index()
    historic_proportions = historic_proportions.sort_index()

    # Align the series with a left join to retain all indices from forecast_proportion
    forecast_proportion, historic_proportions = forecast_proportion.align(
        historic_proportions, join="left", fill_value=0
    )

    placement = forecast_proportion.index.map(categories)

    if historic_proportions.equals(forecast_proportion):
        proportions = pd.DataFrame(
            {
                "Placement": placement,
                "Placement type": forecast_proportion.index,
                "Historic proportion": forecast_proportion.values,
            },
            index=forecast_proportion.index,
        )
    else:
        proportions = pd.DataFrame(
            {
                "Placement": placement,
                "Placement type": forecast_proportion.index,
                "Historic proportion": historic_proportions.values,
                "Forecast proportion": forecast_proportion.values,
            },
            index=forecast_proportion.index,
        )

    proportions = proportions.sort_values(by=["Placement"])
    proportions["Placement"] = proportions["Placement"].mask(
        proportions["Placement"].duplicated(), ""
    )

    proportions = proportions.round(4)

    return proportions


def summary_tables(df):
    """
    takes Costs.summary_table as input and transforms for display
    """
    # round to 2 decimal places
    df = df.round(2)

    # Add a total column
    df["Total"] = df.sum(axis=1)

    # Add a total row
    df.loc["Total"] = df.sum()

    df_transposed = df.T

    return df_transposed


def prediction_chart(
    historic_data: PopulationStats, prediction: Prediction, **kwargs
) -> str:
    """
    Outputs an html figure showing the historic and forecast (with CIs) child populations split by placement type
    """
    # Pop start and end dates to visualise reference period
    reference_start_date = kwargs.pop("reference_start_date")
    reference_end_date = kwargs.pop("reference_end_date")

    prediction.population.index = pd.to_datetime(prediction.population.index)

    forecast_care_by_type_dfs = weekly_care_type_dfs(
        prediction.population,
        value_col="pop_size",
        round_int=True,
    )

    # Dataframe containing total children in historic data
    historic_care_by_type_dfs = weekly_care_type_dfs(
        historic_data.stock,
        value_col="pop_size",
    )

    # Dataframe containing upper and lower confidence intervals
    df_ci = weekly_care_type_dfs(
        prediction.variance,
        value_col="variance",
    )
    df_ci = apply_variances(forecast_care_by_type_dfs, df_ci)

    # Visualise prediction using unstacked dataframe
    fig = go.Figure()

    # Append graph info to population data dictionaries
    historic_care_by_type_dfs["type"] = "Historic"
    historic_care_by_type_dfs["dash"] = "dot"

    forecast_care_by_type_dfs["type"] = "Base forecast"
    forecast_care_by_type_dfs["dash"] = None

    # Add forecast and historical traces
    fig = add_traces(fig, [historic_care_by_type_dfs, forecast_care_by_type_dfs])

    # Append graph info to ci data dictionaries
    df_ci["type"] = "Base forecast"

    # Display confidence interval as filled shape
    fig = add_ci_traces(fig, [df_ci])

    # add shaded reference period
    fig.add_shape(
        type="rect",
        xref="x",
        yref="paper",
        x0=reference_start_date,
        y0=0,
        x1=reference_end_date,
        y1=1,
        line=dict(
            width=0,
        ),
        label=dict(
            text="Reference period", textposition="top center", font=dict(size=14)
        ),
        fillcolor="rgba(105,105,105,0.1)",
        layer="above",
    )

    fig.update_layout(
        title="Forecast child population over time",
        xaxis_title="Date",
        yaxis_title="Number of children",
        hovermode="x unified",
    )
    fig.update_traces(xhoverformat="%d %b %Y")
    fig.update_yaxes(rangemode="tozero")
    fig_html = fig.to_html(full_html=False)
    return fig_html


def historic_chart(data: PopulationStats) -> str:
    """
    Outputs an html figure of the historic child population over time from the stock in population stats
    """
    # Organise the stock dataframe into a dictionary of dataframes split by the categories in an enum
    historic_care_by_type_dfs = weekly_care_type_dfs(
        data.stock,
        value_col="pop_size",
    )

    fig = go.Figure()

    # Append graph info to historic data dictionary
    historic_care_by_type_dfs["type"] = "Historic"
    historic_care_by_type_dfs["dash"] = "dot"

    # Add historical traces
    fig = add_traces(fig, [historic_care_by_type_dfs])

    fig.update_layout(
        title="Historic child population over time",
        xaxis_title="Date",
        yaxis_title="Number of children",
        hovermode="x unified",
    )
    fig.update_yaxes(rangemode="tozero")
    fig_html = fig.to_html(full_html=False)
    return fig_html


def placement_starts_chart(data: PopulationStats) -> str:
    """
    Outputs an html figure of placement counts over time from the stock in population stats
    """
    df = data.df.copy()

    start_date = pd.to_datetime(data.data_start_date)
    end_date = pd.to_datetime(data.data_end_date)

    # --- filter ---
    df = df.loc[
        (df["DECOM"].between(start_date, end_date)) & (df["RNE"] != "Age")
    ].copy()

    # --- normalise to month start ---
    df["date"] = df["DECOM"].dt.to_period("M").dt.to_timestamp()

    # all months in the range
    all_months = pd.date_range(df["date"].min(), df["date"].max(), freq="MS")

    # all unique placement types
    all_types = df["placement_type"].unique()

    # create full combination
    full_index = pd.MultiIndex.from_product(
        [all_months, all_types], names=["date", "placement_type"]
    )

    # group and reindex to full grid, fill missing with 0
    monthly_counts = (
        df.groupby(["date", "placement_type"])
        .size()
        .reindex(full_index, fill_value=0)
        .reset_index(name="count")
    )

    monthly_counts.columns = ["date", "bin", "pop_size"]
    print(monthly_counts)

    monthly_counts_org = care_type_organiser(monthly_counts, "pop_size", "bin")

    # Append graph info to historic data dictionary
    monthly_counts_org["type"] = "Placement starts"
    monthly_counts_org["dash"] = "dot"

    fig = go.Figure()

    fig = add_traces(fig, [monthly_counts_org])

    fig.update_yaxes(rangemode="tozero")

    fig.update_layout(
        title="Placement starts per month",
        xaxis_title="Month",
        yaxis_title="Placements",
        hovermode="x unified",
    )
    fig.update_traces(xhoverformat="%d %b %Y")

    fig_html = fig.to_html(full_html=False)
    return fig_html


def transition_rate_table(data):
    df = data

    # ensures series has accessible column after resetting
    if isinstance(df, pd.Series):
        df = df.rename("rates")

    # reset index
    df = df.reset_index()

    # remove children aging out from transition rates table
    df = remove_age_transitions(df)

    # create duplicate columns, and set index back to original
    df["To"] = df["to"]
    df["From"] = df["from"]
    df.set_index(["from", "to"], inplace=True)

    # filter out children leaving care and rates for children remaining in the placement
    df = df[~df["To"].str.contains("Not in care", na=False)]
    df = df[df["From"] != df["To"]]

    # sort by age groups and then mask duplicate values to give impression of multiindex when displayed
    # sort_values is not used as it sorts lexicographically
    df = rate_table_sort(df, "From", transition=True)

    # if dataframe has 3 columns, order and rename them and round values
    if df.shape[1] == 3:
        df = df[["From", "To", "rates"]]
        df["From"] = df["From"].mask(df["From"].duplicated(), "")
        df.columns = ["From", "To", "Base transition rate"]
        df = df.round(4)

    return df


def exit_rate_table(data):
    """
    Creates columns with duplicate values from index
    Sorts and masks columns to replicate multiindex look
    """
    df = data

    # ensures series has accessible column after resetting
    if isinstance(df, pd.Series):
        df = df.rename("rates")
    # reset index
    df = df.reset_index()

    # keeps only data where children are leaving care
    df = df[df["to"].str.contains("Not in care", na=False)]

    # sets multiindex
    df["From"] = df["from"]
    df.set_index(["from", "to"], inplace=True)

    # sort by age groups and then mask duplicate values to give impression of multiindex when displayed
    # sort_values is not used as it sorts lexicographically
    df = rate_table_sort(df, "From")

    # creates new columns for age and placement from buckets
    try:
        df[["Age Group", "Placement"]] = df["From"].str.split(" - ", expand=True)
    # The above breaks if the data has no children leaving care, so instead we can return
    # an empty dataframe in this instance.
    except:
        df[["Age Group", "Placement"]] = pd.NA

    df = df.drop(columns="From")

    # if dataframe has 3 columns, order and rename them and round values
    if df.shape[1] == 3:
        df = df[["Age Group", "Placement", "rates"]]
        df["Age Group"] = df["Age Group"].mask(df["Age Group"].duplicated(), "")
        df.columns = ["Age Group", "Placement", "Base exit rate"]
        df = df.round(4)

    return df


def entry_rate_table(data):
    """
    Creates columns with duplicate values from index
    Sorts and masks columns to replicate multiindex look
    """
    df = data
    # ensures series has accessible column after resetting
    if isinstance(df, pd.Series):
        df = df.rename("rates")

    # reset index and rename to 'to'
    df = df.reset_index().rename(columns={"index": "to"})

    # filter out not in care population
    df = df[~df["to"].str.contains("Not in care", na=False)]

    # set 'to' back to index
    df["To"] = df["to"]
    df.set_index(["to"], inplace=True)

    # sort by age groups and then mask duplicate values to give impression of multiindex when displayed
    # sort_values is not used as it sorts lexicographically
    df = rate_table_sort(df, "To")

    # split buckets into age group and placement
    df[["Age Group", "Placement"]] = df["To"].str.split(" - ", expand=True)
    df = df.drop(columns="To")

    # if dataframe has 3 columns, order and rename them and round values
    if df.shape[1] == 3:
        df = df[["Age Group", "Placement", "rates"]]
        df["Age Group"] = df["Age Group"].mask(df["Age Group"].duplicated(), "")
        df.columns = ["Age Group", "Placement", "Base entry rate"]
        df = df.round(4)

    return df


def compare_forecast(
    historic_data: PopulationStats,
    base_forecast: Prediction,
    adjusted_forecast: Prediction,
    **kwargs,
) -> str:
    """
    Returns an html graph that is shown to the user when adjustments to transition rates have been made.
    It shows the historic data, the base forecast (with CIs) and the adjusted forecast (with CIs) by placement type.
    """
    # pop start and end dates to visualise reference period
    reference_start_date = kwargs.pop("reference_start_date")
    reference_end_date = kwargs.pop("reference_end_date")

    # historic data organised into dict of dfs by care type bucket
    historic_care_by_type_dfs = weekly_care_type_dfs(
        historic_data.stock,
        value_col="pop_size",
    )

    # dataframe containing total children in base forecast
    forecast_care_by_type_dfs = weekly_care_type_dfs(
        base_forecast.population,
        value_col="pop_size",
        round_int=True,
    )

    # dataframe containing upper and lower confidence intervals for base forecast
    df_ci = weekly_care_type_dfs(
        base_forecast.variance,
        value_col="variance",
    )
    df_ci = apply_variances(forecast_care_by_type_dfs, df_ci)

    # dataframe containing total children in adjusted forecast
    adjusted_care_by_type_dfs = weekly_care_type_dfs(
        adjusted_forecast.population,
        value_col="pop_size",
        round_int=True,
    )

    # dataframe containing upper and lower confidence intervals for adjusted forecast
    df_af_ci = weekly_care_type_dfs(
        adjusted_forecast.variance,
        value_col="variance",
    )
    df_af_ci = apply_variances(adjusted_care_by_type_dfs, df_af_ci)

    # visualise prediction using unstacked dataframe
    fig = go.Figure()

    # Append graph info to population data dictionaries
    for d, label, dash in [
        (historic_care_by_type_dfs, "Historic", "dot"),
        (forecast_care_by_type_dfs, "Base forecast", None),
        (adjusted_care_by_type_dfs, "Adjusted forecast", "dash"),
    ]:
        d["type"] = label
        d["dash"] = dash

    # Add historical and forecast data to figure
    fig = add_traces(
        fig,
        [
            historic_care_by_type_dfs,
            forecast_care_by_type_dfs,
            adjusted_care_by_type_dfs,
        ],
    )

    # Append graph info to ci data dictionaries
    df_ci["type"] = "Base forecast"
    df_af_ci["type"] = "Adjusted forecast"

    # Display confidence interval as filled shape
    fig = add_ci_traces(fig, [df_ci, df_af_ci])

    # add shaded reference period
    fig.add_shape(
        type="rect",
        xref="x",
        yref="paper",
        x0=reference_start_date,
        y0=0,
        x1=reference_end_date,
        y1=1,
        line=dict(
            width=0,
        ),
        label=dict(
            text="Reference period", textposition="top center", font=dict(size=14)
        ),
        fillcolor="rgba(105,105,105,0.1)",
        layer="above",
    )
    fig.update_traces(xhoverformat="%d %b %Y")

    fig.update_layout(
        title="Base and adjusted child population over time",
        xaxis_title="Date",
        yaxis_title="Number of children",
    )
    fig.update_yaxes(rangemode="tozero")
    fig_html = fig.to_html(full_html=False)
    return fig_html


def transition_rate_changes(base, adjusted):
    """
    Takes base and adjusted rate series.
    Combines series
    Transforms
    Filters for only where changes have been made
    Returns None if no changes
    """
    df = pd.concat([base.rename("base"), adjusted.rename("adjusted")], axis=1)

    df = transition_rate_table(df)

    df = df[df["base"] != df["adjusted"]]

    if df.empty:
        return None
    else:
        df = df[["From", "To", "base", "adjusted"]]
        df["From"] = df["From"].mask(df["From"].duplicated(), "")
        df.columns = ["From", "To", "Base transition rate", "Adjusted transition rate"]
        df = df.round(4)
        return df


def exit_rate_changes(base, adjusted):
    """
    Takes base and adjusted rate series.
    Combines series
    Transforms
    Filters for only where changes have been made
    Returns None if no changes
    """
    df = pd.concat([base.rename("base"), adjusted.rename("adjusted")], axis=1)

    df = exit_rate_table(df)

    df = df[df["base"] != df["adjusted"]]

    if df.empty:
        return None
    else:
        df = df[["Age Group", "Placement", "base", "adjusted"]]
        df["Age Group"] = df["Age Group"].mask(df["Age Group"].duplicated(), "")
        df.columns = ["Age Group", "Placement", "Base exit rate", "Adjusted exit rate"]
        df = df.round(4)
        return df


def entry_rate_changes(base, adjusted):
    """
    Takes base and adjusted rate series.
    Combines series
    Transforms
    Filters for only where changes have been made
    Returns None if no changes
    """
    df = pd.concat([base.rename("base"), adjusted.rename("adjusted")], axis=1)

    df = entry_rate_table(df)

    df = df[df["base"] != df["adjusted"]]

    if df.empty:
        return None
    else:
        df = df[["Age Group", "Placement", "base", "adjusted"]]
        df["Age Group"] = df["Age Group"].mask(df["Age Group"].duplicated(), "")
        df.columns = [
            "Age Group",
            "Placement",
            "Base entry rate",
            "Adjusted entry rate",
        ]
        df = df.round(4)
        return df
