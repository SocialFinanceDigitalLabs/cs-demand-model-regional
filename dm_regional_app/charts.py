import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from dm_regional_app.utils import (
    add_ci_traces,
    add_traces,
    apply_variances,
    care_type_organiser,
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


def area_chart_cost(historic_data: CostForecast, prediction: CostForecast):
    df_forecast = prediction.costs

    df_forecast = df_forecast.melt(
        var_name="Placement",
        value_name="Cost",
        ignore_index=False,
    )

    # extract prediction start date
    prediction_start_date = df_forecast.index.min()

    # repeat transformation for historic data
    df_historic = historic_data.costs
    df_historic = df_historic.melt(
        var_name="Placement",
        value_name="Cost",
        ignore_index=False,
    )

    # filter any data after the prediction start date
    df_historic = df_historic[df_historic.index <= prediction_start_date]

    # combine Costs
    combined_df = df_forecast.combine_first(df_historic)

    fig = px.area(
        combined_df,
        x=combined_df.index,
        y="Cost",
        color="Placement",
        labels={"index": "Date", "Cost": "Cost in £"},
    )
    fig.add_vline(
        x=prediction_start_date, line_width=1, line_dash="dash", line_color="black"
    )
    fig.update_layout(title="Child placement costs")
    fig_html = fig.to_html(full_html=False)
    return fig_html


def area_chart_population(historic_data: CostForecast, prediction: CostForecast):
    df_forecast = prediction.proportional_population

    df_forecast = df_forecast.melt(
        var_name="Placement",
        value_name="Population",
        ignore_index=False,
    )
    df_forecast.index = pd.to_datetime(df_forecast.index)

    # extract prediction start date
    prediction_start_date = df_forecast.index.min()

    # repeat transformation for historic data
    df_historic = historic_data.proportional_population
    df_historic = df_historic.melt(
        var_name="Placement",
        value_name="Population",
        ignore_index=False,
    )
    df_historic.index = pd.to_datetime(df_historic.index)

    # filter any data after the prediction start date
    df_historic = df_historic[df_historic.index <= prediction_start_date]

    # combine populations
    combined_df = df_forecast.combine_first(df_historic)

    fig = px.area(
        combined_df,
        x=combined_df.index,
        y="Population",
        color="Placement",
        labels={
            "index": "Date",
        },
    )
    fig.add_vline(
        x=prediction_start_date, line_width=1, line_dash="dash", line_color="black"
    )
    fig.update_layout(title="Child placement numbers")
    fig_html = fig.to_html(full_html=False)
    return fig_html


def placement_proportion_table(data: CostForecast):
    proportions = data.proportions

    categories = {item.value.label: item.value.category.label for item in Costs}

    placement = proportions.index.map(categories)

    proportions = pd.DataFrame(
        {
            "Placement": placement,
            "Placement type": proportions.index,
            "Current proportion": proportions.values,
        },
        index=proportions.index,
    )

    proportions = proportions.sort_values(by=["Placement"])
    proportions["Placement"] = proportions["Placement"].mask(
        proportions["Placement"].duplicated(), ""
    )

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


def prediction_chart(historic_data: PopulationStats, prediction: Prediction, **kwargs):
    # Pop start and end dates to visualise reference period
    reference_start_date = kwargs.pop("reference_start_date")
    reference_end_date = kwargs.pop("reference_end_date")

    # Dataframe containing total children in prediction
    df = prediction.population.unstack().reset_index()

    df.columns = ["from", "date", "forecast"]
    # Organises forecast data into dict of dfs by care type bucket
    forecast_care_by_type_dfs = care_type_organiser(df)

    # Dataframe containing total children in historic data
    df_hd = historic_data.stock.unstack().reset_index()
    df_hd.columns = ["from", "date", "historic"]
    # Organises historic data into dict of dfs by care type bucket
    historic_care_by_type_dfs = care_type_organiser(df_hd)

    # Dataframe containing upper and lower confidence intervals
    df_ci = prediction.variance.unstack().reset_index()
    df_ci.columns = ["from", "date", "variance"]
    # Organises confidence interval data into dict of dfs by care type bucket
    df_ci = care_type_organiser(df_ci)

    df_ci = apply_variances(forecast_care_by_type_dfs, df_ci)

    # Visualise prediction using unstacked dataframe
    fig = go.Figure()

    # Add forecast and historical traces
    fig = add_traces(forecast_care_by_type_dfs, historic_care_by_type_dfs, fig)

    # Display confidence interval as filled shape
    fig = add_ci_traces(df_ci, fig)

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
        title="Forecast", xaxis_title="Date", yaxis_title="Number of children"
    )
    fig.update_yaxes(rangemode="tozero")
    fig_html = fig.to_html(full_html=False)
    return fig_html


def historic_chart(data: PopulationStats):
    df_hd = data.stock.unstack().reset_index()
    df_hd.columns = ["from", "date", "historic"]
    historic_care_by_type_dfs = care_type_organiser(df_hd)

    fig = go.Figure()

    # Add historical traces
    fig = add_traces(None, historic_care_by_type_dfs, fig)

    fig.update_layout(title="Historic data")
    fig.update_yaxes(rangemode="tozero")
    fig_html = fig.to_html(full_html=False)
    return fig_html


def transition_rate_table(data):
    df = data

    # ensures series has accessible column after resetting
    if isinstance(df, pd.Series):
        df = df.rename("rates")

    # reset index, create duplicate columns, and set index back to original
    df = df.reset_index()
    df["To"] = df["to"]
    df["From"] = df["from"]
    df.set_index(["from", "to"], inplace=True)

    # filter out children leaving care and rates for children remaining in the placement
    df = df[df["To"].apply(lambda x: "Not in care" in x) == False]
    df = df[df["From"] != df["To"]]

    # sort by age groups and then mask duplicate values to give impression of multiindex when displayed
    df = df.sort_values(by=["From"])
    df["From"] = df["From"].mask(df["From"].duplicated(), "")

    # if dataframe has 3 columns, order and rename them and round values
    if df.shape[1] == 3:
        df = df[["From", "To", "rates"]]
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
    df = df[df["to"].apply(lambda x: "Not in care" in x)]

    # creates new columns for age and placement from buckets
    df[["Age Group", "Placement"]] = df["from"].str.split(" - ", expand=True)

    # sets multiindex
    df.set_index(["from", "to"], inplace=True)

    # sort by age groups and then mask duplicate values to give impression of multiindex when displayed
    df = df.sort_values(by=["Age Group"])
    df["Age Group"] = df["Age Group"].mask(df["Age Group"].duplicated(), "")

    # if dataframe has 3 columns, order and rename them and round values
    if df.shape[1] == 3:
        df = df[["Age Group", "Placement", "rates"]]
        df.columns = ["Age Group", "Placement", "Base entry rate"]
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
    df = df[df["to"].apply(lambda x: "Not in care" in x) == False]

    # split buckets into age group and placement
    df[["Age Group", "Placement"]] = df["to"].str.split(" - ", expand=True)

    # set 'to' back to index
    df.set_index(["to"], inplace=True)

    # sort by age groups and then mask duplicate values to give impression of multiindex when displayed
    df = df.sort_values(by=["Age Group"])
    df["Age Group"] = df["Age Group"].mask(df["Age Group"].duplicated(), "")

    # if dataframe has 3 columns, order and rename them and round values
    if df.shape[1] == 3:
        df = df[["Age Group", "Placement", "rates"]]
        df.columns = ["Age Group", "Placement", "Base entry rate"]
        df = df.round(4)

    return df


def compare_forecast(
    historic_data: PopulationStats,
    base_forecast: Prediction,
    adjusted_forecast: Prediction,
    **kwargs
):
    # pop start and end dates to visualise reference period
    reference_start_date = kwargs.pop("reference_start_date")
    reference_end_date = kwargs.pop("reference_end_date")

    # dataframe containing total children in historic data
    df_hd = historic_data.stock.unstack().reset_index()
    df_hd.columns = ["from", "date", "historic"]
    df_hd = df_hd[["date", "historic"]].groupby(by="date").sum().reset_index()
    df_hd["date"] = pd.to_datetime(df_hd["date"]).dt.date

    # dataframe containing total children in base forecast
    df = base_forecast.population.unstack().reset_index()

    df.columns = ["from", "date", "forecast"]
    df = df[df["from"].apply(lambda x: "Not in care" in x) == False]
    df = df[["date", "forecast"]].groupby(by="date").sum().reset_index()
    df["date"] = pd.to_datetime(df["date"]).dt.date

    # dataframe containing upper and lower confidence intervals for base forecast
    df_ci = base_forecast.variance.unstack().reset_index()
    df_ci.columns = ["bin", "date", "variance"]
    df_ci = df_ci[["date", "variance"]].groupby(by="date").sum().reset_index()
    df_ci["date"] = pd.to_datetime(df_ci["date"]).dt.date
    df_ci["upper"] = df["forecast"] + df_ci["variance"]
    df_ci["lower"] = df["forecast"] - df_ci["variance"]

    # dataframe containing total children in adjusted forecast
    df_af = adjusted_forecast.population.unstack().reset_index()

    df_af.columns = ["from", "date", "forecast"]
    df_af = df_af[df_af["from"].apply(lambda x: "Not in care" in x) == False]
    df_af = df_af[["date", "forecast"]].groupby(by="date").sum().reset_index()
    df_af["date"] = pd.to_datetime(df_af["date"]).dt.date

    # dataframe containing upper and lower confidence intervals for adjusted forecast
    df_df_ci = adjusted_forecast.variance.unstack().reset_index()
    df_df_ci.columns = ["bin", "date", "variance"]
    df_df_ci = df_df_ci[["date", "variance"]].groupby(by="date").sum().reset_index()
    df_df_ci["date"] = pd.to_datetime(df_df_ci["date"]).dt.date
    df_df_ci["upper"] = df_af["forecast"] + df_df_ci["variance"]
    df_df_ci["lower"] = df_af["forecast"] - df_df_ci["variance"]

    # visualise prediction using unstacked dataframe
    fig = go.Figure()

    # Display confidence interval as filled shape
    fig.add_trace(
        go.Scatter(
            x=df_df_ci["date"],
            y=df_df_ci["lower"],
            line_color="rgba(255,255,255,0)",
            name="Adjusted confidence interval",
            showlegend=False,
        )
    )

    fig.add_trace(
        go.Scatter(
            x=df_df_ci["date"],
            y=df_df_ci["upper"],
            fill="tonexty",
            fillcolor="rgba(255,140,0,0.2)",
            line_color="rgba(255,255,255,0)",
            name="Adjusted confidence interval",
            showlegend=True,
        )
    )

    # Display confidence interval as filled shape
    fig.add_trace(
        go.Scatter(
            x=df_df_ci["date"],
            y=df_ci["lower"],
            line_color="rgba(255,255,255,0)",
            name="Base confidence interval",
            showlegend=False,
        )
    )

    fig.add_trace(
        go.Scatter(
            x=df_df_ci["date"],
            y=df_df_ci["upper"],
            fill="tonexty",
            fillcolor="rgba(0,176,246,0.2)",
            line_color="rgba(255,255,255,0)",
            name="Base confidence interval",
            showlegend=True,
        )
    )

    # add base forecast for total children
    fig.add_trace(
        go.Scatter(
            x=df_af["date"],
            y=df_af["forecast"],
            name="Adjusted Forecast",
            line=dict(color="black", width=1.5, dash="dash"),
        )
    )

    # add adjusted forecast for total children
    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["forecast"],
            name="Base Forecast",
            line=dict(color="black", width=1.5),
        )
    )

    # add historic data for total children
    fig.add_trace(
        go.Scatter(
            x=df_hd["date"],
            y=df_hd["historic"],
            name="Historic data",
            line=dict(color="black", width=1.5, dash="dot"),
        )
    )

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
        title="Forecast", xaxis_title="Date", yaxis_title="Number of children"
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

    df = df[df["base"] != df["adjusted"]]

    if df.empty:
        return None
    else:
        df = transition_rate_table(df)
        df = df[["From", "To", "base", "adjusted"]]
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

    df = df[df["base"] != df["adjusted"]]

    if df.empty:
        return None
    else:
        df = exit_rate_table(df)
        df = df[["Age Group", "Placement", "base", "adjusted"]]
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

    df = df[df["base"] != df["adjusted"]]

    if df.empty:
        return None
    else:
        df = entry_rate_table(df)
        df = df[["Age Group", "Placement", "base", "adjusted"]]
        df.columns = [
            "Age Group",
            "Placement",
            "Base entry rate",
            "Adjusted entry rate",
        ]
        df = df.round(4)
        return df
