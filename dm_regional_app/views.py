from django.shortcuts import render

import plotly.express as px
from dm_regional_app.predictor import predict
from dm_regional_app.forms import PredictFilter
import numpy as np
import datetime


def chart_view(request):
    if request.method == 'POST':
        form = PredictFilter(request.POST)
        if form.is_valid():
            start_date = form.cleaned_data['start_date']
            end_date = form.cleaned_data['end_date']
            # Call predict function with the provided dates
            df = predict(
                source="sample://v1.zip", # in the future, this will probably point to some S3 bucket with regiomal 903 files.
                start=start_date,
                end=end_date,
            )
            # Render the result along with the form
            # unstack predicted dataframe
            df_pp = df.unstack().reset_index()
            df_pp.columns = ["from", "date", "value"]

            # visualise prediction using unstacked dataframe
            fig = px.line(df_pp, y="value", x="date", color="from")
            fig.update_layout(title="Prediction")
            fig_html = fig.to_html(full_html=False)

            return render(request, "dm_regional_app/chart.html", context={'form': form, "chart": fig_html})
    else:
        form = PredictFilter()
        # Call predict function with the provided dates
        df = predict(
            source="sample://v1.zip", # in the future, this will probably point to some S3 bucket with regiomal 903 files.
        )
        # Render the result along with the form
        # unstack predicted dataframe
        df_pp = df.unstack().reset_index()
        df_pp.columns = ["from", "date", "value"]

        # visualise prediction using unstacked dataframe
        fig = px.line(df_pp, y="value", x="date", color="from")
        fig.update_layout(title="Prediction")
        fig_html = fig.to_html(full_html=False)
    return render(request, "dm_regional_app/chart.html", {'form': form, "chart": fig_html})

