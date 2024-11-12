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

    df_forecast = df_forecast.melt(
        var_name="Placement",
        value_name="Cost",
        ignore_index=False,
    )

    # extract prediction start date
    prediction_start_date = df_forecast.index.min()

    # repeat transformation for historic data
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


def area_chart_population(historic_data: pd.DataFrame, prediction: CostForecast):
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
    df_historic = historic_data
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

    # Dataframe containing total children in prediction
    df = prediction.population.unstack().reset_index()

    df.columns = ["bin", "date", "pop_size"]
    # Organises forecast data into dict of dfs by care type bucket
    forecast_care_by_type_dfs = care_type_organiser(df, "pop_size", "bin")

    # Dataframe containing total children in historic data
    df_hd = historic_data.stock.unstack().reset_index()
    df_hd.columns = ["bin", "date", "pop_size"]
    # Organises historic data into dict of dfs by care type bucket
    historic_care_by_type_dfs = care_type_organiser(df_hd, "pop_size", "bin")

    # Dataframe containing upper and lower confidence intervals
    df_ci = prediction.variance.unstack().reset_index()
    df_ci.columns = ["bin", "date", "variance"]
    # Organises confidence interval data into dict of dfs by care type bucket
    df_ci = care_type_organiser(df_ci, "variance", "bin")

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
    )
    fig.update_yaxes(rangemode="tozero")
    fig_html = fig.to_html(full_html=False)
    return fig_html


def historic_chart(data: PopulationStats) -> str:
    """
    Outputs an html figure of the historic child population over time from the stock in population stats
    """
    # Organise the stock dataframe into a dictionary of dataframes split by the categories in an enum
    df_hd = data.stock.unstack().reset_index()
    df_hd.columns = ["bin", "date", "pop_size"]
    historic_care_by_type_dfs = care_type_organiser(df_hd, "pop_size", "bin")

    fig = go.Figure()

    # Append graph info to historic data dictionary
    historic_care_by_type_dfs["type"] = "Historic"
    historic_care_by_type_dfs["dash"] = "dot"

    # Add historical traces
    fig = add_traces(fig, [historic_care_by_type_dfs])

    fig.update_layout(title="Historic child population over time")
    fig.update_yaxes(rangemode="tozero")
    fig_html = fig.to_html(full_html=False)
    return fig_html


def placement_starts_chart(data: PopulationStats, start_date: str, end_date: str):
    data.df["DECOM"] = pd.to_datetime(data.df["DECOM"])
    start_date, end_date = pd.to_datetime([start_date, end_date])
    data.df["DECOM"] = data.df["DECOM"].dt.to_period("M").dt.to_timestamp()

    # filter time-frame to form dates
    df_filtered = data.df[
        (data.df["DECOM"] >= start_date) & (data.df["DECOM"] <= end_date)
    ]

    # calculate placement duration (end_age - age)
    df_filtered["placement_duration"] = df_filtered["end_age"] - df_filtered["age"]
    # Create a range of all months to ensure we have complete months
    all_months = pd.date_range(start=start_date, end=end_date, freq="M")

    # Group by 'placement_type' and aggregate
    df_entrants = (
        df_filtered.groupby(
            ["placement_type", pd.Grouper(key="DECOM", freq="M")]
        )  # Group by month
        .agg(count=("CHILD", "size"), avg_duration=("placement_duration", "mean"))
        .reset_index()  # Reset index after grouping
    )

    df_entrants = (
        df_entrants.set_index(["DECOM", "placement_type"])
        .reindex(
            pd.MultiIndex.from_product(
                [all_months, df_entrants["placement_type"].unique()],
                names=["DECOM", "placement_type"],
            ),
            fill_value=0,
        )
        .reset_index()
    )

    # convert avg_duration yrs to more sensical wks (using 52.14 wks pa)
    df_entrants["avg_duration_weeks"] = (df_entrants["avg_duration"] * 52.14).round(2)

    df_entrants["true_count"] = df_entrants["count"]
    # min and max vals for y
    min_count = df_entrants["true_count"].min()
    max_count = df_entrants["true_count"].max()

    # visualise
    fig = px.line(
        df_entrants,
        y="count",
        x="DECOM",
        color="placement_type",
        markers=True,
        line_shape="spline",
        labels={
            "count": "Placements",
            "DECOM": "Date",
            "placement_type": "Placement Type",
            "avg_duration_weeks": "Avg Duration (wks)",
        },
        # title="Placement starts per month by Placement Type",
        hover_data={"true_count": True, "avg_duration_weeks": True},
    )

    quarterly_months = df_entrants[
        df_entrants["DECOM"].dt.month.isin([1, 4, 7, 10])
    ]  # reduce labels only Jan, Apr, Jul, Oct for clarity
    max_count = df_entrants["count"].max()

    fig.update_layout(
        xaxis=dict(
            tickvals=quarterly_months["DECOM"],
            ticktext=[
                f"{d:%b}" for d in quarterly_months["DECOM"]
            ],  # qtr/mth abbr (Jan, Apr, Jul, Oct)
            tickangle=45,
            tickmode="array",
            title=dict(text="Date", standoff=40),
        ),
        title="Placement starts per month by Placement Type",
        hovermode="x",
        font=dict(size=12),
    )

    for year in df_entrants["DECOM"].dt.year.unique():
        fig.add_annotation(
            x=f"{year}-07-01",  # center yr labels
            y=-0.18,
            text=str(year),
            showarrow=False,
            xref="x",
            yref="paper",
            align="center",
        )

    fig.update_traces(line=dict(width=1), marker=dict(size=4))

    # min and max date vals for x
    fig.update_xaxes(
        title_text="Date",
        range=[
            df_entrants["DECOM"].min(),
            df_entrants["DECOM"].max(),
        ],  # Use min and max date values
    )

    # ensure y-axis min to max vals
    fig.update_yaxes(
        title_text="Placements",
        range=[
            min_count,
            max_count * 1.1,
        ],  # raise y-axis to give top end data visual space
        tickvals=list(
            range(int(min_count), int(max_count) + 10, 10)
        ),  # generate tick marks
        ticktext=[str(i) for i in range(int(min_count), int(max_count) + 10, 10)],
    )
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
    df = df[df["To"].apply(lambda x: "Not in care" in x) == False]
    df = df[df["From"] != df["To"]]

    # sort by age groups and then mask duplicate values to give impression of multiindex when displayed
    # sort_values is not used as it sorts  lexicographically
    df = rate_table_sort(df, "From", transition=True)
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
    try:
        df[["Age Group", "Placement"]] = df["from"].str.split(" - ", expand=True)
    # The above breaks if the data has no children leaving care, so instead we can return
    # an empty dataframe in this instance.
    except:
        df[["Age Group", "Placement"]] = pd.NA

    # sets multiindex
    df.set_index(["from", "to"], inplace=True)

    # sort by age groups and then mask duplicate values to give impression of multiindex when displayed
    # sort_values is not used as it sorts  lexicographically
    df = rate_table_sort(df, "Age Group")
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
    # sort_values is not used as it sorts  lexicographically
    df = rate_table_sort(df, "Age Group")
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
    **kwargs,
) -> str:
    """
    Returns an html graph that is shown to the user when adjustments to transition rates have been made.
    It shows the historic data, the base forecast (with CIs) and the adjusted forecast (with CIs) by placement type.
    """
    # pop start and end dates to visualise reference period
    reference_start_date = kwargs.pop("reference_start_date")
    reference_end_date = kwargs.pop("reference_end_date")

    # dataframe containing total children in historic data
    df_hd = historic_data.stock.unstack().reset_index()
    df_hd.columns = ["bin", "date", "pop_size"]
    # Organises historic data into dict of dfs by care type bucket
    historic_care_by_type_dfs = care_type_organiser(df_hd, "pop_size", "bin")

    # dataframe containing total children in base forecast
    df_base = base_forecast.population.unstack().reset_index()

    df_base.columns = ["bin", "date", "pop_size"]
    # Organises forecast data into dict of dfs by care type bucket
    forecast_care_by_type_dfs = care_type_organiser(df_base, "pop_size", "bin")

    # dataframe containing upper and lower confidence intervals for base forecast
    df_ci = base_forecast.variance.unstack().reset_index()
    df_ci.columns = ["bin", "date", "variance"]
    # Organises confidence interval data into dict of dfs by care type bucket
    df_ci = care_type_organiser(df_ci, "variance", "bin")

    df_ci = apply_variances(forecast_care_by_type_dfs, df_ci)

    # dataframe containing total children in adjusted forecast
    df_af = adjusted_forecast.population.unstack().reset_index()
    df_af.columns = ["bin", "date", "pop_size"]
    adjusted_care_by_type_dfs = care_type_organiser(df_af, "pop_size", "bin")

    # dataframe containing upper and lower confidence intervals for adjusted forecast
    df_af_ci = adjusted_forecast.variance.unstack().reset_index()
    df_af_ci.columns = ["bin", "date", "variance"]
    # Organises adjusted confidence interval data into dict of dfs by care type bucket
    df_af_ci = care_type_organiser(df_af_ci, "variance", "bin")

    df_af_ci = apply_variances(adjusted_care_by_type_dfs, df_af_ci)

    # visualise prediction using unstacked dataframe
    fig = go.Figure()

    # Append graph info to population data dictionaries
    historic_care_by_type_dfs["type"] = "Historic"
    historic_care_by_type_dfs["dash"] = "dot"

    forecast_care_by_type_dfs["type"] = "Base forecast"
    forecast_care_by_type_dfs["dash"] = None

    adjusted_care_by_type_dfs["type"] = "Adjusted forecast"
    adjusted_care_by_type_dfs["dash"] = "dash"

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

    df = df[df["base"] != df["adjusted"]]

    df = transition_rate_table(df)

    if df.empty:
        return None
    else:
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

    df = exit_rate_table(df)

    if df.empty:
        return None
    else:
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

    df = entry_rate_table(df)

    if df.empty:
        return None
    else:
        df = df[["Age Group", "Placement", "base", "adjusted"]]
        df.columns = [
            "Age Group",
            "Placement",
            "Base entry rate",
            "Adjusted entry rate",
        ]
        df = df.round(4)
        return df
