from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from dm_regional_app.charts import historic_chart, prediction_chart
from dm_regional_app.forms import HistoricDataFilter, PredictFilter
from dm_regional_app.models import SavedScenario, SessionScenario
from dm_regional_app.utils import apply_filters
from ssda903 import Config
from ssda903.population_stats import PopulationStats
from ssda903.predictor import predict
from ssda903.reader import read_data


def home(request):
    return render(request, "dm_regional_app/views/home.html")


@login_required
def router_handler(request):
    # get next url page
    next_url_name = request.GET.get("next_url_name")

    # initialise a SessionScenario when the user is coming from a direct link to any of the views
    session_scenario_id = request.session.get("session_scenario_id", None)
    current_user = request.user

    # read data
    datacontainer = read_data(source=settings.DATA_SOURCE)

    historic_filters = {
        "la": [],
        "placement_types": [],
        "age_bins": [],
        "uasc": "all",
    }

    # this is stand in code to be edited when prediction page is improved
    prediction_filters = {"buckets": []}
    prediction_parameters = {
        "reference_start_date": datacontainer.start_date,
        # delete - relativedelta(months=6) just for testing before datacontainer fix
        "reference_end_date": datacontainer.end_date - relativedelta(months=6),
        "prediction_start_date": None,
        "prediction_end_date": None,
    }
    historic_stock = {
        "population": {},
        "base_rates": [],
        "adjusted_rates": [],
    }
    adjusted_costs = {"adjusted_costs": []}

    # default_values should define the model default parameters, like reference_date and the stock data and so on. Decide what should be default with Michael
    session_scenario, created = SessionScenario.objects.get_or_create(
        id=session_scenario_id,
        defaults={
            "user_id": current_user.id,
            "historic_filters": historic_filters,
            "prediction_filters": prediction_filters,
            "prediction_parameters": prediction_parameters,
            "historic_stock": historic_stock,
            "adjusted_costs": adjusted_costs,
        },
    )

    # update the request session
    request.session["session_scenario_id"] = session_scenario.pk
    return redirect(next_url_name)


@login_required
def prediction(request):
    if "session_scenario_id" in request.session:
        pk = request.session["session_scenario_id"]
        session_scenario = get_object_or_404(SessionScenario, pk=pk)
        # read data
        datacontainer = read_data(source=settings.DATA_SOURCE)

        if request.method == "POST":
            if "uasc" in request.POST:
                historic_form = HistoricDataFilter(
                    request.POST,
                    la=datacontainer.unique_las,
                    placement_types=datacontainer.unique_placement_types,
                    age_bins=datacontainer.unique_age_bins,
                )
                predict_form = PredictFilter(
                    initial=session_scenario.prediction_parameters
                )
                if historic_form.is_valid():
                    session_scenario.historic_filters = historic_form.cleaned_data
                    session_scenario.save()
                    print(request.POST)

                    historic_data = apply_filters(
                        datacontainer.enriched_view, historic_form.cleaned_data
                    )

            if "reference_start_date" in request.POST:
                predict_form = PredictFilter(request.POST)
                historic_form = HistoricDataFilter(
                    initial=session_scenario.historic_filters,
                    la=datacontainer.unique_las,
                    placement_types=datacontainer.unique_placement_types,
                    age_bins=datacontainer.unique_age_bins,
                )
                if predict_form.is_valid():
                    session_scenario.prediction_parameters = predict_form.cleaned_data
                    session_scenario.save()
                    print(request.POST)
                    print(session_scenario.prediction_parameters)
                    historic_data = apply_filters(
                        datacontainer.enriched_view, session_scenario.historic_filters
                    )

        else:
            historic_form = HistoricDataFilter(
                initial=session_scenario.historic_filters,
                la=datacontainer.unique_las,
                placement_types=datacontainer.unique_placement_types,
                age_bins=datacontainer.unique_age_bins,
            )
            historic_data = apply_filters(
                datacontainer.enriched_view, historic_form.initial
            )

            # initialize form with default dates
            predict_form = PredictFilter(initial=session_scenario.prediction_parameters)

        config = Config()
        stats = PopulationStats(historic_data, config)

        # Call predict function with default dates
        prediction = predict(
            data=historic_data, **session_scenario.prediction_parameters
        )

        # build chart
        chart = prediction_chart(stats, prediction)

        return render(
            request,
            "dm_regional_app/views/prediction.html",
            {
                "predict_form": predict_form,
                "historic_form": historic_form,
                "chart": chart,
            },
        )
    else:
        next_url_name = "router_handler"
        # Construct the URL for the router handler view and append the next_url_name as a query parameter
        redirect_url = reverse(next_url_name) + "?next_url_name=" + "prediction"
        return redirect(redirect_url)


@login_required
def historic_data(request):
    if "session_scenario_id" in request.session:
        pk = request.session["session_scenario_id"]
        session_scenario = get_object_or_404(SessionScenario, pk=pk)
        config = Config()
        # read data
        datacontainer = read_data(source=settings.DATA_SOURCE)

        if request.method == "POST":
            # initialize form with data
            form = HistoricDataFilter(
                request.POST,
                la=datacontainer.unique_las,
                placement_types=datacontainer.unique_placement_types,
                age_bins=datacontainer.unique_age_bins,
            )

            if form.is_valid():
                # save cleaned data to session scenarios historic filters
                session_scenario.historic_filters = form.cleaned_data
                session_scenario.save()

                # update reference start and end

                data = apply_filters(datacontainer.enriched_view, form.cleaned_data)
            else:
                data = datacontainer.enriched_view
        else:
            # read data
            datacontainer = read_data(source=settings.DATA_SOURCE)

            # initialize form with default dates
            form = HistoricDataFilter(
                initial=session_scenario.historic_filters,
                la=datacontainer.unique_las,
                placement_types=datacontainer.unique_placement_types,
                age_bins=datacontainer.unique_age_bins,
            )
            data = apply_filters(datacontainer.enriched_view, form.initial)

        entry_into_care_count = data.loc[
            data.placement_type_before
            == datacontainer.config.PlacementCategories.NOT_IN_CARE
        ]["CHILD"].nunique()
        exiting_care_count = data.loc[
            data.placement_type_after
            == datacontainer.config.PlacementCategories.NOT_IN_CARE
        ]["CHILD"].nunique()

        config = Config()
        stats = PopulationStats(data, config)

        chart = historic_chart(stats)

        return render(
            request,
            "dm_regional_app/views/historic.html",
            {
                "form": form,
                "entry_into_care_count": entry_into_care_count,
                "exiting_care_count": exiting_care_count,
                "chart": chart,
            },
        )
    else:
        next_url_name = "router_handler"
        # Construct the URL for the router handler view and append the next_url_name as a query parameter
        redirect_url = reverse(next_url_name) + "?next_url_name=" + "historic_data"
        return redirect(redirect_url)


@login_required
def scenarios(request):
    user = request.user
    scenarios = SavedScenario.objects.filter(user=user)
    return render(
        request, "dm_regional_app/views/scenarios.html", {"scenarios": scenarios}
    )


@login_required
def scenario_detail(request, pk):
    scenario = get_object_or_404(SavedScenario, pk=pk, user=request.user)
    return render(
        request, "dm_regional_app/views/scenario_detail.html", {"scenario": scenario}
    )
