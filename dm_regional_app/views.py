from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from dm_regional_app.charts import prediction_chart
from dm_regional_app.forms import HistoricDataFilter, PredictFilter
from dm_regional_app.models import Scenario
from ssda903.predictor import predict
from ssda903.reader import read_data


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
def prediction(request):
    # read data
    datacontainer = read_data(source=settings.DATA_SOURCE)

    if request.method == "POST":
        # initialize form with data
        form = PredictFilter(request.POST)

        if form.is_valid():
            start_date = form.cleaned_data["start_date"]
            end_date = form.cleaned_data["end_date"]

        else:
            start_date = datacontainer.end_date - relativedelta(months=6)
            end_date = datacontainer.end_date

    else:
        # set default dates
        start_date = datacontainer.end_date - relativedelta(months=6)
        end_date = datacontainer.end_date

        # initialize form with default dates
        form = PredictFilter(
            initial={
                "start_date": start_date,
                "end_date": end_date,
            }
        )

    # Call predict function with default dates
    prediction = predict(
        data=datacontainer.enriched_view,
        start=start_date,
        end=end_date,
    )

    # build chart
    chart = prediction_chart(prediction)
    return render(
        request, "dm_regional_app/views/prediction.html", {"form": form, "chart": chart}
    )


@login_required
def historic_data(request):
    if request.method == "POST":
        # read data
        datacontainer = read_data(source=settings.DATA_SOURCE)

        # initialize form with data
        form = HistoricDataFilter(
            request.POST,
            la_choices=datacontainer.unique_las,
            placement_type_choices=datacontainer.unique_placement_types,
        )
        if form.is_valid():
            data = form.apply_filters(datacontainer.enriched_view)
        else:
            data = datacontainer.enriched_view
    else:
        # read data
        datacontainer = read_data(source=settings.DATA_SOURCE)

        # initialize form with default dates
        form = HistoricDataFilter(
            initial={
                "start_date": datacontainer.start_date,
                "end_date": datacontainer.end_date,
            },
            la_choices=datacontainer.unique_las,
            placement_type_choices=datacontainer.unique_placement_types,
        )
        data = datacontainer.enriched_view

    # TODO AMY - create the relevant charts from this dataset, according to the designs
    entry_into_care_count = data.loc[
        data.placement_type_before
        == datacontainer.config.PlacementCategories.NOT_IN_CARE
    ]["CHILD"].nunique()
    exiting_care_count = data.loc[
        data.placement_type_after
        == datacontainer.config.PlacementCategories.NOT_IN_CARE
    ]["CHILD"].nunique()

    return render(
        request,
        "dm_regional_app/views/historic.html",
        {
            "form": form,
            "entry_into_care_count": entry_into_care_count,
            "exiting_care_count": exiting_care_count,
        },
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
