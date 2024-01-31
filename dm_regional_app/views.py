from django.shortcuts import render

import plotly.express as px
from dm_regional_app.predictor import predict


def chart_view(request):
    df = predict(
        source="sample://v1.zip", # in the future, this will probably point to some S3 bucket with regiomal 903 files.
    )

    # predicted dataframe
    print(df)

    # TODO - use df to create a plotly figure
    x = [1, 2, 3]
    y = [4, 1, 2]
    fig = px.bar(x=x, y=y)
    fig.update_layout(title="Other Plot")
    fig_html = fig.to_html(full_html=False)

    return render(request, "dm_regional_app/chart.html", context={"chart": fig_html})
