import plotly.express as px
from demand_model.multinomial.predictor import Prediction

from ssda903.datacontainer import DemandModellingDataContainer
from ssda903.population_stats import PopulationStats


def prediction_chart(prediction: Prediction):
    df_pp = prediction.population.unstack().reset_index()
    df_pp.columns = ["from", "date", "value"]

    # visualise prediction using unstacked dataframe
    fig = px.line(df_pp, y="value", x="date", color="from")
    fig.update_layout(title="Prediction")
    fig_html = fig.to_html(full_html=False)
    return fig_html


def historic_chart(data: PopulationStats):
    df_pp = data.stock.unstack().reset_index()
    df_pp.columns = ["from", "date", "value"]

    # visualise prediction using unstacked dataframe
    fig = px.line(df_pp, y="value", x="date", color="from")
    fig.update_layout(title="Prediction")
    fig_html = fig.to_html(full_html=False)
    return fig_html
