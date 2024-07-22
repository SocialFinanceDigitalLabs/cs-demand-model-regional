import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from ssda903.config import Costs
from ssda903.costs import CostForecast
from ssda903.multinomial import Prediction
from ssda903.population_stats import PopulationStats


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


def prediction_chart(historic_data: PopulationStats, prediction: Prediction, **kwargs):
    # pop start and end dates to visualise reference period
    reference_start_date = kwargs.pop("reference_start_date")
    reference_end_date = kwargs.pop("reference_end_date")

    # dataframe containing total children in prediction
    df = prediction.population.unstack().reset_index()

    df.columns = ["from", "date", "forecast"]
    df = df[df["from"].apply(lambda x: "Not in care" in x) == False]
    df = df[["date", "forecast"]].groupby(by="date").sum().reset_index()
    df["date"] = pd.to_datetime(df["date"]).dt.date

    # dataframe containing total children in historic data
    df_hd = historic_data.stock.unstack().reset_index()
    df_hd.columns = ["from", "date", "historic"]
    df_hd = df_hd[["date", "historic"]].groupby(by="date").sum().reset_index()
    df_hd["date"] = pd.to_datetime(df_hd["date"]).dt.date

    # dataframe containing upper and lower confidence intervals
    df_ci = prediction.variance.unstack().reset_index()
    df_ci.columns = ["bin", "date", "variance"]
    df_ci = df_ci[["date", "variance"]].groupby(by="date").sum().reset_index()
    df_ci["date"] = pd.to_datetime(df_ci["date"]).dt.date
    df_ci["upper"] = df["forecast"] + df_ci["variance"]
    df_ci["lower"] = df["forecast"] - df_ci["variance"]

    # visualise prediction using unstacked dataframe
    fig = go.Figure()

    # Display confidence interval as filled shape
    fig.add_trace(
        go.Scatter(
            x=df_ci["date"],
            y=df_ci["lower"],
            line_color="rgba(255,255,255,0)",
            name="Confidence interval",
            showlegend=False,
        )
    )

    fig.add_trace(
        go.Scatter(
            x=df_ci["date"],
            y=df_ci["upper"],
            fill="tonexty",
            fillcolor="rgba(0,176,246,0.2)",
            line_color="rgba(255,255,255,0)",
            name="Confidence interval",
            showlegend=True,
        )
    )

    # add forecast for total children
    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["forecast"],
            name="Forecast",
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


def historic_chart(data: PopulationStats):
    df_hd = data.stock.unstack().reset_index()
    df_hd.columns = ["from", "date", "value"]
    df_hd = df_hd[["date", "value"]].groupby(by="date").sum().reset_index()

    # visualise prediction using unstacked dataframe
    fig = px.line(
        df_hd,
        y="value",
        x="date",
        labels={
            "value": "Number of children",
            "date": "Date",
        },
    )
    fig.update_layout(title="Historic data")
    fig.update_yaxes(rangemode="tozero")
    fig_html = fig.to_html(full_html=False)
    return fig_html


def transition_rate_table(data):
    df = data

    df = df.reset_index()
    df["To"] = df["to"]
    df["From"] = df["from"]
    df.set_index(["from", "to"], inplace=True)
    df = df[df["To"].apply(lambda x: "Not in care" in x) == False]
    df = df.round(4)
    df = df.sort_values(by=["From"])
    df = df[df["From"] != df["To"]]
    df["From"] = df["From"].mask(df["From"].duplicated(), "")

    to = df.pop("To")
    df.insert(0, "To", to)
    from_col = df.pop("From")
    df.insert(0, "From", from_col)

    df.columns = ["From", "To", "Base transition rate"]

    return df


def exit_rate_table(data):
    df = data

    df = df.reset_index()
    df["From"] = df["from"]
    df = df[df["to"].apply(lambda x: "Not in care" in x)]
    df.set_index(["from", "to"], inplace=True)
    df = df.round(4)

    df[["Age Group", "Placement"]] = df["From"].str.split(" - ", expand=True)

    placement = df.pop("Placement")
    df.insert(0, "Placement", placement)

    age_group = df.pop("Age Group")
    df.insert(0, "Age Group", age_group)

    df = df.drop(["From"], axis=1)

    df = df.sort_values(by=["Age Group"])
    df["Age Group"] = df["Age Group"].mask(df["Age Group"].duplicated(), "")

    df.columns = ["Age Group", "Placement", "Base exit rate"]

    return df


def entry_rate_table(data):
    df = data

    df = df.reset_index()
    df["to"] = df["index"]
    df = df[df["to"].apply(lambda x: "Not in care" in x) == False]

    df = df.round(4)

    df[["Age Group", "Placement"]] = df["to"].str.split(" - ", expand=True)
    df.set_index(["to"], inplace=True)

    placement = df.pop("Placement")
    df.insert(0, "Placement", placement)

    age_group = df.pop("Age Group")
    df.insert(0, "Age Group", age_group)

    df = df.sort_values(by=["Age Group"])
    df["Age Group"] = df["Age Group"].mask(df["Age Group"].duplicated(), "")

    df = df.drop(["index"], axis=1)

    df.columns = ["Age Group", "Placement", "Base entry rate"]

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
            x=df_ci["date"],
            y=df_ci["lower"],
            line_color="rgba(255,255,255,0)",
            name="Base confidence interval",
            showlegend=False,
        )
    )

    fig.add_trace(
        go.Scatter(
            x=df_ci["date"],
            y=df_ci["upper"],
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
