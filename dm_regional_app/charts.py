import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from demand_model.multinomial.predictor import Prediction

from ssda903.population_stats import PopulationStats


def prediction_chart(historic_data: PopulationStats, prediction: Prediction, **kwargs):
    # pop start and end dates to visualise reference period
    reference_start_date = kwargs.pop("reference_start_date")
    reference_end_date = kwargs.pop("reference_end_date")

    # dataframe containing total children in prediction
    df = prediction.population.unstack().reset_index()
    df.columns = ["from", "date", "forecast"]
    df = df[df["from"].apply(lambda x: "NOT_IN_CARE" in x[1]) == False]
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
        title="Base forecast", xaxis_title="Date", yaxis_title="Number of children"
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


def transistion_rate_table(data):
    df = data

    df.columns = pd.MultiIndex.from_tuples(df.columns, names=["Age", "Placement"])
    df = df.reset_index()
    df = df[df["to"].apply(lambda x: "NOT_IN_CARE" in x[1]) == False]
    df.drop("NOT_IN_CARE", axis=1, level=1, inplace=True)
    df[["Age", "Placement"]] = pd.DataFrame(df["to"].tolist(), index=df.index)
    placement = df.pop("Placement")
    df.insert(0, "Placement", placement)
    age = df.pop("Age")
    df.insert(0, "Age", age)
    df.drop("to", axis=1, inplace=True)
    df = df.round(4)
    df["Age"] = df["Age"].mask(df["Age"].duplicated(), "")

    cols = df.columns.to_frame().T
    cols = cols.transpose()
    cols["Age"] = cols["Age"].mask(cols["Age"].duplicated(), "")
    cols = cols.transpose()

    return df, cols
