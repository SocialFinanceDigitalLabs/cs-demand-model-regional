import pandas as pd
import plotly.express as px
from demand_model.multinomial.predictor import Prediction

from ssda903.datacontainer import DemandModellingDataContainer
from ssda903.population_stats import PopulationStats


def prediction_chart(historic_data: PopulationStats, prediction: Prediction):
    df = prediction.population.unstack().reset_index()
    df.columns = ["from", "date", "forecast"]
    df = df[["date", "forecast"]].groupby(by="date").sum().reset_index()
    df["date"] = pd.to_datetime(df["date"])

    df_hd = historic_data.stock.unstack().reset_index()
    df_hd.columns = ["from", "date", "historic"]
    df_hd = df_hd[["date", "historic"]].groupby(by="date").sum().reset_index()
    df_hd["date"] = pd.to_datetime(df_hd["date"])

    df = pd.merge(df, df_hd, how="outer", on="date", indicator=True)
    df = df.melt(id_vars=["date"], value_vars=["historic", "forecast"])

    # visualise prediction using unstacked dataframe
    fig = px.line(
        df,
        y="value",
        x="date",
        labels={
            "value": "Number of children",
            "date": "Date",
        },
        color="variable",
    )
    fig.update_layout(title="Prediction")
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
