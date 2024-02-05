from django.shortcuts import render

import plotly.express as px
from dm_regional_app.predictor import predict
import pandas as pd


def chart_view(request):
    df = predict(
        source="sample://v1.zip", # in the future, this will probably point to some S3 bucket with regiomal 903 files.
    )

    # predicted dataframe
    print(df)

    # TODO - use df to create a plotly figure
    
    
    df_pp = df.unstack().reset_index()
    df_pp.columns = ["from", "date", "value"]
    print(df_pp)

    fig = px.line(df_pp, y="value", x="date", color="from")
    fig.update_layout(title="Prediction")
    fig_html = fig.to_html(full_html=False)

    return render(request, "dm_regional_app/chart.html", context={"chart": fig_html})
