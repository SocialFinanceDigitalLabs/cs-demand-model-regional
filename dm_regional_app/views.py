import plotly.express as px
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from dm_regional_app.forms import PredictFilter
from dm_regional_app.models import Scenario
from dm_regional_app.predictor import predict


def home(request):
    return render(request, "dm_regional_app/views/home.html")


@login_required
def dashboard(request):
    user = request.user
    scenarios = Scenario.objects.filter(user=user)
    return render(
        request, "dm_regional_app/views/dashboard.html", {"scenarios": scenarios}
    )


@login_required
def chart_view(request):
    if request.method == "POST":
        form = PredictFilter(request.POST)
        if form.is_valid():
            start_date = form.cleaned_data["start_date"]
            end_date = form.cleaned_data["end_date"]
            # Call predict function with the provided dates
            prediction = predict(
                source="sample://v1.zip",  # in the future, this will probably point to some S3 bucket with regiomal 903 files.
                start=start_date,
                end=end_date,
            )
            # Render the result along with the form
            # unstack predicted dataframe
            df_pp = prediction.population.unstack().reset_index()
            df_pp.columns = ["from", "date", "value"]

            # visualise prediction using unstacked dataframe
            fig = px.line(df_pp, y="value", x="date", color="from")
            fig.update_layout(title="Prediction")
            fig_html = fig.to_html(full_html=False)

            return render(
                request,
                "dm_regional_app/views/chart.html",
                context={"form": form, "chart": fig_html},
            )
    else:
        form = PredictFilter()
        # Call predict function with the provided dates
        prediction = predict(
            source="sample://v1.zip",  # in the future, this will probably point to some S3 bucket with regiomal 903 files.
        )
        # Render the result along with the form
        # unstack predicted dataframe
        df_pp = prediction.population.unstack().reset_index()
        df_pp.columns = ["from", "date", "value"]

        # visualise prediction using unstacked dataframe
        fig = px.line(df_pp, y="value", x="date", color="from")
        fig.update_layout(title="Prediction")
        fig_html = fig.to_html(full_html=False)
    return render(
        request, "dm_regional_app/views/chart.html", {"form": form, "chart": fig_html}
    )


@login_required
def scenarios(request):
    user = request.user
    scenarios = Scenario.objects.filter(user=user)
    return render(
        request, "dm_regional_app/views/scenarios.html", {"scenarios": scenarios}
    )


@login_required
def scenario_detail(request, pk):
    scenario = get_object_or_404(Scenario, pk=pk, user=request.user)
    return render(
        request, "dm_regional_app/views/scenario_detail.html", {"scenario": scenario}
    )
