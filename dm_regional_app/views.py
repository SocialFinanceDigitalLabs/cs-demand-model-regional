import time
from pathlib import Path

import pandas as pd
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.storage import default_storage
from django.forms.models import model_to_dict
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django_tables2 import RequestConfig

from dm_regional_app.charts import (
    area_chart_cost,
    area_chart_population,
    compare_forecast,
    entry_rate_changes,
    entry_rate_table,
    exit_rate_changes,
    exit_rate_table,
    historic_chart,
    placement_proportion_table,
    prediction_chart,
    summary_tables,
    transition_rate_changes,
    transition_rate_table,
    year_one_costs,
)
from dm_regional_app.decorators import user_is_admin
from dm_regional_app.filters import SavedScenarioFilter
from dm_regional_app.forms import (
    DataSourceUploadForm,
    DynamicForm,
    HistoricDataFilter,
    InflationForm,
    PredictFilter,
    SavedScenarioForm,
)
from dm_regional_app.models import DataSource, SavedScenario, SessionScenario
from dm_regional_app.tables import SavedScenarioTable
from dm_regional_app.utils import apply_filters, number_format, save_data_if_not_empty
from ssda903.config import PlacementCategories
from ssda903.costs import (
    convert_historic_population_to_cost,
    convert_population_to_cost,
)
from ssda903.population_stats import PopulationStats
from ssda903.predictor import predict
from ssda903.reader import read_data, read_local_data


def home(request):
    return render(request, "dm_regional_app/views/home.html")


@login_required
def router_handler(request):
    print("router_handler time start")
    rh_total_start_time = time.time()

    # get next url page
    next_url_name = request.GET.get("next_url_name")

    # initialise a SessionScenario when the user is coming from a direct link to any of the views
    session_scenario_id = request.session.get("session_scenario_id", None)
    current_user = request.user

    # read data
    rh_dc_start_time = time.time()
    datacontainer = read_data(source=settings.DATA_SOURCE)
    rh_dc_end_time = time.time()
    dc_exec_time = rh_dc_start_time - rh_dc_end_time
    print(f"rh_dc_time = {dc_exec_time}")

    historic_filters = {
        "la": [],
        "ethnicity": [],
        "sex": "all",
        "uasc": "all",
    }

    prediction_parameters = {
        "reference_start_date": datacontainer.start_date,
        "reference_end_date": datacontainer.end_date,
        "prediction_start_date": None,
        "prediction_end_date": None,
    }
    historic_stock = {
        "population": {},
        "base_rates": [],
    }
    adjusted_costs = None

    adjusted_rates = None

    adjusted_proportions = None

    inflation_parameters = {
        "inflation": False,
        "inflation_rate": 0.1,
    }

    # default_values should define the model default parameters, like reference_date and the stock data and so on. Decide what should be default with Michael
    session_scenario, created = SessionScenario.objects.get_or_create(
        id=session_scenario_id,
        defaults={
            "user_id": current_user.id,
            "historic_filters": historic_filters,
            "prediction_parameters": prediction_parameters,
            "historic_stock": historic_stock,
            "adjusted_costs": adjusted_costs,
            "adjusted_rates": adjusted_rates,
            "adjusted_proportions": adjusted_proportions,
            "inflation_parameters": inflation_parameters,
        },
    )

    # update the request session
    request.session["session_scenario_id"] = session_scenario.pk

    rh_total_end_time = time.time()
    rh_total_exec_time = rh_total_end_time - rh_total_start_time
    print(f"router_handler time end, total exec = {rh_total_exec_time}")

    return redirect(next_url_name)


@login_required
def costs(request):
    if "session_scenario_id" in request.session:
        print("costs time start")
        costs_total_start_time = time.time()
        pk = request.session["session_scenario_id"]
        session_scenario = get_object_or_404(SessionScenario, pk=pk)

        if request.method == "POST":
            form = InflationForm(request.POST)
            if form.is_valid():
                session_scenario.inflation_parameters = form.cleaned_data
                session_scenario.save()

        else:
            inflation_parameters = session_scenario.inflation_parameters.copy()
            form = InflationForm(initial=inflation_parameters)

        # read data
        costs_dc_start_time = time.time()
        datacontainer = read_data(source=settings.DATA_SOURCE)
        costs_dc_end_time = time.time()
        costs_dc_exec_time = costs_dc_end_time - costs_dc_start_time
        print(f"costs dc exec time = {costs_dc_exec_time}")

        historic_data = apply_filters(
            datacontainer.enriched_view, session_scenario.historic_filters
        )

        historic_filters = session_scenario.historic_filters

        # Call predict function
        costs_pred_start_time = time.time()
        prediction = predict(
            data=historic_data,
            **session_scenario.prediction_parameters,
            rate_adjustment=session_scenario.adjusted_rates,
            number_adjustment=session_scenario.adjusted_numbers,
        )
        costs_pred_end_time = time.time()
        costs_pred_exec_time = costs_pred_end_time - costs_pred_start_time
        print(f"costs pred exec time = {costs_pred_exec_time}")

        costs_stats_start_time = time.time()
        stats = PopulationStats(historic_data)
        costs_stats_end_time = time.time()
        costs_stats_exec_time = costs_stats_end_time - costs_stats_start_time
        print(f"costs stats exec time = {costs_stats_exec_time}")

        (
            historic_placement_proportions,
            historic_population,
        ) = stats.placement_proportions(**session_scenario.prediction_parameters)

        costs = convert_population_to_cost(
            prediction,
            historic_placement_proportions,
            session_scenario.adjusted_costs,
            session_scenario.adjusted_proportions,
            **session_scenario.inflation_parameters,
        )

        historic_costs = convert_historic_population_to_cost(
            historic_population, session_scenario.adjusted_costs
        )

        costs_base_pred_start = time.time()
        base_prediction = predict(
            data=historic_data, **session_scenario.prediction_parameters
        )
        costs_base_pred_end = time.time()
        costs_base_pred_exec = costs_base_pred_end - costs_base_pred_start
        print(f"costs base pred exec = {costs_base_pred_exec}")

        base_costs = convert_population_to_cost(
            base_prediction,
            historic_placement_proportions,
            session_scenario.adjusted_costs,
            **session_scenario.inflation_parameters,
        )

        weekly_cost = pd.DataFrame(
            {
                "Placement type": costs.cost_summary.index,
                "Weekly cost": costs.cost_summary.values,
            }
        )

        area_numbers = area_chart_population(historic_population, costs)

        area_costs = area_chart_cost(historic_costs, costs)

        proportions = placement_proportion_table(historic_placement_proportions, costs)

        summary_table = summary_tables(costs.summary_table)

        summary_table_base = summary_tables(base_costs.summary_table)

        summary_table_difference = summary_table - summary_table_base
        summary_table_difference = summary_table_difference.round(2)

        year_one_cost = year_one_costs(costs)
        year_one_cost_base = year_one_costs(base_costs)
        year_one_cost_difference = year_one_cost - year_one_cost_base
        year_one_cost = number_format(year_one_cost)
        year_one_cost_base = number_format(year_one_cost_base)
        year_one_cost_difference = number_format(year_one_cost_difference)

        if session_scenario.adjusted_rates is not None:
            transition_rate_table = transition_rate_changes(
                base_prediction.transition_rates, prediction.transition_rates
            )
            exit_rate_table = exit_rate_changes(
                base_prediction.transition_rates, prediction.transition_rates
            )
        else:
            transition_rate_table = None
            exit_rate_table = None

        if session_scenario.adjusted_numbers is not None:
            entry_rate_table = entry_rate_changes(
                base_prediction.entry_rates, prediction.entry_rates
            )
        else:
            entry_rate_table = None

        costs_end_time = time.time()
        costs_exec = costs_end_time = costs_total_start_time
        print(f"costs total exec = {costs_exec}")
        return render(
            request,
            "dm_regional_app/views/costs.html",
            {
                "forecast_dates": session_scenario.prediction_parameters,
                "weekly_cost": weekly_cost,
                "proportions": proportions,
                "area_numbers": area_numbers,
                "area_costs": area_costs,
                "summary_table": summary_table,
                "summary_table_base": summary_table_base,
                "summary_table_difference": summary_table_difference,
                "year_one_cost": year_one_cost,
                "year_one_cost_base": year_one_cost_base,
                "year_one_cost_difference": year_one_cost_difference,
                "historic_filters": historic_filters,
                "transition_rate_table": transition_rate_table,
                "exit_rate_table": exit_rate_table,
                "entry_rate_table": entry_rate_table,
                "form": form,
            },
        )
    else:
        next_url_name = "router_handler"
        # Construct the URL for the router handler view and append the next_url_name as a query parameter
        redirect_url = reverse(next_url_name) + "?next_url_name=" + "costs"
        return redirect(redirect_url)


@login_required
def save_scenario(request):
    if "session_scenario_id" in request.session:
        print("save_scenario start")
        save_scen_start = time.time()
        pk = request.session["session_scenario_id"]
        session_scenario = get_object_or_404(SessionScenario, pk=pk)
        current_user = request.user

        if (
            session_scenario.saved_scenario
            and session_scenario.saved_scenario.user == current_user
        ):
            related_scenario = True
            scenario_to_update = session_scenario.saved_scenario
            form = SavedScenarioForm(instance=scenario_to_update)

        else:
            related_scenario = False
            form = SavedScenarioForm()

        if request.method == "POST":
            if "update" in request.POST:
                form = SavedScenarioForm(request.POST, instance=scenario_to_update)

                if form.is_valid():
                    # Convert the session scenario to a dictionary, excluding fields you don't want to copy
                    session_data = model_to_dict(
                        session_scenario, exclude=["id", "saved_scenario", "user"]
                    )

                    for key, value in session_data.items():
                        setattr(scenario_to_update, key, value)

                    # Update with additional fields from the form
                    scenario_to_update.name = form.cleaned_data["name"]
                    scenario_to_update.description = form.cleaned_data["description"]
                    scenario_to_update.save()

                    messages.success(request, "Scenario updated.")
                    save_scen_end_1 = time.time()
                    save_scen_exec_1 = save_scen_end_1 - save_scen_start
                    print(f"save scen 1 exec = {save_scen_exec_1}")
                    return redirect("scenarios")

            else:
                form = SavedScenarioForm(request.POST)

                if form.is_valid():
                    # Convert the session scenario to a dictionary, excluding fields you don't want to copy
                    session_data = model_to_dict(
                        session_scenario, exclude=["id", "saved_scenario", "user"]
                    )

                    # Create the SavedScenario instance
                    saved_scenario = SavedScenario.objects.create(
                        **session_data, user_id=current_user.id
                    )

                    # Update with additional fields from the form
                    saved_scenario.name = form.cleaned_data["name"]
                    saved_scenario.description = form.cleaned_data["description"]
                    saved_scenario.save()

                    # Associate the saved scenario with the session scenario
                    session_scenario.saved_scenario = saved_scenario
                    session_scenario.save()

                    messages.success(request, "Scenario saved.")

                    save_scen_end_2 = time.time()
                    save_scen_exec_2 = save_scen_end_2 - save_scen_start
                    print(f"save scen 2 exec = {save_scen_exec_2}")
                    return redirect("scenarios")

        save_scen_end_3 = time.time()
        save_scen_exec_3 = save_scen_end_3 - save_scen_start
        print(f"save scen 3 exec = {save_scen_exec_3}")
        return render(
            request,
            "dm_regional_app/views/save_scenario.html",
            {
                "form": form,
                "related_scenario": related_scenario,
            },
        )
    else:
        next_url_name = "router_handler"
        # Construct the URL for the router handler view and append the next_url_name as a query parameter
        redirect_url = reverse(next_url_name) + "?next_url_name=" + "save_scenario"
        return redirect(redirect_url)


@login_required
def clear_proportion_adjustments(request):
    if "session_scenario_id" in request.session:
        # get next url page
        next_url_name = request.GET.get("next_url_name")
        pk = request.session["session_scenario_id"]
        session_scenario = get_object_or_404(SessionScenario, pk=pk)
        session_scenario.adjusted_proportions = None
        session_scenario.save()
        messages.success(request, "Proportion adjustments cleared.")
    return redirect(next_url_name)


@login_required
def placement_proportions(request):
    if "session_scenario_id" in request.session:
        print("placement proportions start")
        place_prop_start = time.time()

        pk = request.session["session_scenario_id"]
        session_scenario = get_object_or_404(SessionScenario, pk=pk)
        # read data
        place_prop_dc_start = time.time()
        datacontainer = read_data(source=settings.DATA_SOURCE)
        place_prop_dc_end = time.time()
        place_prop_dc_exec = place_prop_dc_end - place_prop_dc_start
        print(f"place prop dc exec = {place_prop_dc_exec}")

        historic_data = apply_filters(
            datacontainer.enriched_view, session_scenario.historic_filters
        )

        # Call predict function
        place_prop_pred_start = time.time()
        prediction = predict(
            data=historic_data, **session_scenario.prediction_parameters
        )
        place_prop_pred_end = time.time()
        place_prop_pred_exec = place_prop_pred_end - place_prop_pred_start
        print(f"place prop pred exec = {place_prop_pred_exec}")

        place_prop_stats_start = time.time()
        stats = PopulationStats(historic_data)
        place_prop_stats_end = time.time()
        place_prop_stats_exec = place_prop_stats_end - place_prop_stats_start
        print(f"place prop stats exec = {place_prop_stats_exec}")

        (
            historic_placement_proportions,
            historic_population,
        ) = stats.placement_proportions(**session_scenario.prediction_parameters)

        costs = convert_population_to_cost(
            prediction,
            historic_placement_proportions,
            session_scenario.adjusted_costs,
            session_scenario.adjusted_proportions,
        )

        proportions = placement_proportion_table(historic_placement_proportions, costs)

        if request.method == "POST":
            form = DynamicForm(
                request.POST,
                dataframe=costs.proportions,
                initial_data=session_scenario.adjusted_proportions,
            )
            if form.is_valid():
                data = form.save()

                if session_scenario.adjusted_proportions is not None:
                    # if previous proportion adjustments have been made, update old series with new adjustments
                    proportion_adjustments = session_scenario.adjusted_proportions
                    new_numbers = data.combine_first(proportion_adjustments)

                    session_scenario.adjusted_proportions = new_numbers
                    session_scenario.save()

                else:
                    # Check that the dataframe or series saved in the form is not empty, then save
                    if isinstance(data, (pd.DataFrame, pd.Series)) and not data.empty:
                        session_scenario.adjusted_proportions = data
                        session_scenario.save()

                place_prop_end_1 = time.time()
                place_prop_exec_1 = place_prop_end_1 - place_prop_start
                print(f"place prop exec 1 = {place_prop_exec_1}")
                return redirect("costs")

            else:
                form = DynamicForm(
                    request.POST,
                    dataframe=costs.proportions,
                    initial_data=session_scenario.adjusted_proportions,
                )
                messages.warning(request, "Form not saved, positive numbers only")

                place_prop_end_2 = time.time()
                place_prop_exec_2 = place_prop_end_2 - place_prop_start
                print(f"place prop exec 2 = {place_prop_exec_2}")
                return render(
                    request,
                    "dm_regional_app/views/placement_proportions.html",
                    {
                        "form": form,
                        "placement_types": proportions,
                    },
                )

        else:
            form = DynamicForm(
                dataframe=costs.proportions,
                initial_data=session_scenario.adjusted_proportions,
            )

            place_prop_end_3 = time.time()
            place_prop_exec_3 = place_prop_end_3 - place_prop_start
            print(f"place prop exec 3 = {place_prop_exec_3}")
            return render(
                request,
                "dm_regional_app/views/placement_proportions.html",
                {
                    "form": form,
                    "placement_types": proportions,
                },
            )
    else:
        next_url_name = "router_handler"
        # Construct the URL for the router handler view and append the next_url_name as a query parameter
        redirect_url = (
            reverse(next_url_name) + "?next_url_name=" + "placement_proportions"
        )
        return redirect(redirect_url)


@login_required
def weekly_costs(request):
    if "session_scenario_id" in request.session:
        print("weekly costs start")
        weekly_costs_start = time.time()
        pk = request.session["session_scenario_id"]
        session_scenario = get_object_or_404(SessionScenario, pk=pk)
        # read data
        weekly_costs_dc_start = time.time()
        datacontainer = read_data(source=settings.DATA_SOURCE)
        weekly_costs_dc_end = time.time()
        weekly_costs_dc_exec = weekly_costs_dc_end - weekly_costs_dc_start
        print(f"weekly costs dc exec = {weekly_costs_dc_exec}")

        historic_data = apply_filters(
            datacontainer.enriched_view, session_scenario.historic_filters
        )

        # Call predict function
        weekly_costs_pred_start = time.time()
        prediction = predict(
            data=historic_data, **session_scenario.prediction_parameters
        )
        weekly_costs_pred_end = time.time()
        weekly_costs_pred_exec = weekly_costs_pred_end - weekly_costs_pred_start
        print(f"weekly costs pred exec = {weekly_costs_pred_exec}")

        weekly_costs_stats_start = time.time()
        stats = PopulationStats(historic_data)
        weekly_costs_stats_end = time.time()
        weekly_costs_stats_exec = weekly_costs_stats_end - weekly_costs_stats_start
        print(f"weekly costs stats exec = {weekly_costs_stats_exec}")

        placement_proportions, historic_population = stats.placement_proportions(
            **session_scenario.prediction_parameters
        )

        costs = convert_population_to_cost(
            prediction,
            placement_proportions,
            session_scenario.adjusted_costs,
            session_scenario.adjusted_proportions,
        )

        placement_types = pd.DataFrame(
            {"Placement type": costs.cost_summary.index}, index=costs.cost_summary.index
        )

        if request.method == "POST":
            form = DynamicForm(
                request.POST,
                dataframe=costs.cost_summary,
                initial_data=costs.cost_summary,
            )
            if form.is_valid():
                data = form.save()

                if session_scenario.adjusted_costs is not None:
                    # if previous cost adjustments have been made, update old series with new adjustments
                    cost_adjustments = session_scenario.adjusted_costs
                    new_numbers = data.combine_first(cost_adjustments)

                    session_scenario.adjusted_costs = new_numbers
                    session_scenario.save()

                else:
                    # Check that the dataframe or series saved in the form is not empty, then save
                    save_data_if_not_empty(session_scenario, data, "adjusted_costs")

                weekly_costs_end_1 = time.time()
                weekly_costs_exec_1 = weekly_costs_end_1 - weekly_costs_start
                print(f"weekly costs exec 1 = {weekly_costs_exec_1}")
                return redirect("costs")

            else:
                messages.warning(request, "Form not saved, positive numbers only")
                weekly_costs_end_2 = time.time()
                weekly_costs_exec_2 = weekly_costs_end_2 - weekly_costs_start
                print(f"weekly costs exec 2 = {weekly_costs_exec_2}")
                return render(
                    request,
                    "dm_regional_app/views/weekly_costs.html",
                    {
                        "form": form,
                        "placement_types": placement_types,
                    },
                )

        else:
            form = DynamicForm(
                dataframe=costs.cost_summary,
                initial_data=costs.cost_summary,
            )

            weekly_costs_end_3 = time.time()
            weekly_costs_exec_3 = weekly_costs_end_3 - weekly_costs_start
            print(f"weekly costs exec 3 = {weekly_costs_exec_3}")
            return render(
                request,
                "dm_regional_app/views/weekly_costs.html",
                {
                    "form": form,
                    "placement_types": placement_types,
                },
            )
    else:
        next_url_name = "router_handler"
        # Construct the URL for the router handler view and append the next_url_name as a query parameter
        redirect_url = reverse(next_url_name) + "?next_url_name=" + "weekly_costs"
        return redirect(redirect_url)


@login_required
def load_saved_scenario(request, pk):
    print("load saved scenario start")
    load_scen_start = time.time()
    # loading save scenario should copy it over to a session scenario and jump to the predict view with it
    saved_scenario = get_object_or_404(SavedScenario, pk=pk)

    current_user = request.user

    if saved_scenario.user.profile.la == current_user.profile.la:
        scenario_data = model_to_dict(
            saved_scenario, exclude=["id", "name", "description", "user"]
        )
        session_scenario = SessionScenario.objects.create(
            **scenario_data, user_id=current_user.id
        )

        # we are keeping the saved_scenario in the session_scenario because we might need it if the user decides to update this saved instance
        session_scenario.saved_scenario = saved_scenario
        session_scenario.save()

        # update the request session
        request.session["session_scenario_id"] = session_scenario.pk

        messages.success(
            request,
            "Scenario loaded. Current page will not show additional adjustments, click 'next' or navigate to Adjust Forecast to view these.",
        )

        load_scen_end_1 = time.time()
        load_scen_exec_1 = load_scen_end_1 - load_scen_start
        print(f"load scen exec 1 = {load_scen_exec_1}")
        return redirect("prediction")

    else:
        messages.warning(
            request,
            "Scenario not loaded, can only load scenarios associated with your current local authority",
        )
        load_scen_end_2 = time.time()
        load_scen_exec_2 = load_scen_end_2 - load_scen_start
        print(f"load scen exec 2 = {load_scen_exec_2}")
        return redirect("scenarios")


@login_required
def clear_rate_adjustments(request):
    if "session_scenario_id" in request.session:
        # get next url page
        next_url_name = request.GET.get("next_url_name")
        pk = request.session["session_scenario_id"]
        session_scenario = get_object_or_404(SessionScenario, pk=pk)
        session_scenario.adjusted_rates = None
        session_scenario.adjusted_numbers = None
        session_scenario.save()
        messages.success(request, "Rate adjustments cleared.")
    return redirect(next_url_name)


@login_required
def entry_rates(request):
    if "session_scenario_id" in request.session:
        print("entry rates start")
        entry_rates_start = time.time()
        pk = request.session["session_scenario_id"]
        session_scenario = get_object_or_404(SessionScenario, pk=pk)
        # read data
        entry_rates_dc_start = time.time()
        datacontainer = read_data(source=settings.DATA_SOURCE)
        entry_rates_dc_end = time.time()
        entry_rates_dc_exec = entry_rates_dc_end - entry_rates_dc_start
        print(f"entry rates dc exec = {entry_rates_dc_exec}")

        historic_data = apply_filters(
            datacontainer.enriched_view, session_scenario.historic_filters
        )

        # Call predict function
        prediction = predict(
            data=historic_data, **session_scenario.prediction_parameters
        )

        entry_rates = entry_rate_table(prediction.entry_rates)

        if request.method == "POST":
            form = DynamicForm(
                request.POST,
                dataframe=prediction.entry_rates,
                initial_data=session_scenario.adjusted_numbers,
            )
            if form.is_valid():
                data = form.save()

                if session_scenario.adjusted_numbers is not None:
                    # if previous rate adjustments have been made, update old series with new adjustments
                    rate_adjustments = session_scenario.adjusted_numbers
                    new_numbers = data.combine_first(rate_adjustments)

                    session_scenario.adjusted_numbers = new_numbers
                    session_scenario.save()

                else:
                    # Check that the dataframe or series saved in the form is not empty, then save
                    save_data_if_not_empty(session_scenario, data, "adjusted_numbers")

                stats = PopulationStats(historic_data)

                adjusted_prediction = predict(
                    data=historic_data,
                    **session_scenario.prediction_parameters,
                    rate_adjustment=session_scenario.adjusted_rates,
                    number_adjustment=session_scenario.adjusted_numbers,
                )

                # build chart
                chart = compare_forecast(
                    stats,
                    prediction,
                    adjusted_prediction,
                    **session_scenario.prediction_parameters,
                )

                is_post = True

                return render(
                    request,
                    "dm_regional_app/views/entry_rates.html",
                    {
                        "entry_rate_table": entry_rates,
                        "form": form,
                        "chart": chart,
                        "is_post": is_post,
                    },
                )
            else:
                messages.warning(request, "Form not saved, positive numbers only")
                form = DynamicForm(
                    request.POST,
                    initial_data=session_scenario.adjusted_numbers,
                    dataframe=prediction.entry_rates,
                )

                is_post = False

                return render(
                    request,
                    "dm_regional_app/views/entry_rates.html",
                    {
                        "entry_rate_table": entry_rates,
                        "form": form,
                        "is_post": is_post,
                    },
                )

        else:
            form = DynamicForm(
                initial_data=session_scenario.adjusted_numbers,
                dataframe=prediction.entry_rates,
            )

            is_post = False

        return render(
            request,
            "dm_regional_app/views/entry_rates.html",
            {
                "entry_rate_table": entry_rates,
                "form": form,
                "is_post": is_post,
            },
        )
    else:
        next_url_name = "router_handler"
        # Construct the URL for the router handler view and append the next_url_name as a query parameter
        redirect_url = reverse(next_url_name) + "?next_url_name=" + "entry_rates"
        return redirect(redirect_url)


@login_required
def exit_rates(request):
    if "session_scenario_id" in request.session:
        pk = request.session["session_scenario_id"]
        session_scenario = get_object_or_404(SessionScenario, pk=pk)
        # read data
        datacontainer = read_data(source=settings.DATA_SOURCE)

        historic_data = apply_filters(
            datacontainer.enriched_view, session_scenario.historic_filters
        )

        # Call predict function
        prediction = predict(
            data=historic_data, **session_scenario.prediction_parameters
        )

        exit_rates = exit_rate_table(prediction.transition_rates)

        if request.method == "POST":
            form = DynamicForm(
                request.POST,
                dataframe=prediction.transition_rates,
                initial_data=session_scenario.adjusted_rates,
            )
            if form.is_valid():
                data = form.save()

                if session_scenario.adjusted_rates is not None:
                    # if previous rate adjustments have been made, update old series with new adjustments
                    rate_adjustments = session_scenario.adjusted_rates
                    new_rates = data.combine_first(rate_adjustments)

                    session_scenario.adjusted_rates = new_rates
                    session_scenario.save()

                else:
                    # Check that the dataframe or series saved in the form is not empty, then save
                    save_data_if_not_empty(session_scenario, data, "adjusted_rates")

                stats = PopulationStats(historic_data)

                adjusted_prediction = predict(
                    data=historic_data,
                    **session_scenario.prediction_parameters,
                    rate_adjustment=session_scenario.adjusted_rates,
                    number_adjustment=session_scenario.adjusted_numbers,
                )

                # build chart
                chart = compare_forecast(
                    stats,
                    prediction,
                    adjusted_prediction,
                    **session_scenario.prediction_parameters,
                )

                is_post = True

                return render(
                    request,
                    "dm_regional_app/views/exit_rates.html",
                    {
                        "exit_rate_table": exit_rates,
                        "form": form,
                        "chart": chart,
                        "is_post": is_post,
                    },
                )

            else:
                form = DynamicForm(
                    request.POST,
                    initial_data=session_scenario.adjusted_rates,
                    dataframe=prediction.transition_rates,
                )
                messages.warning(request, "Form not saved, positive numbers only")

                is_post = False

            return render(
                request,
                "dm_regional_app/views/exit_rates.html",
                {
                    "exit_rate_table": exit_rates,
                    "form": form,
                    "is_post": is_post,
                },
            )

        else:
            form = DynamicForm(
                initial_data=session_scenario.adjusted_rates,
                dataframe=prediction.transition_rates,
            )

            is_post = False

        return render(
            request,
            "dm_regional_app/views/exit_rates.html",
            {
                "exit_rate_table": exit_rates,
                "form": form,
                "is_post": is_post,
            },
        )
    else:
        next_url_name = "router_handler"
        # Construct the URL for the router handler view and append the next_url_name as a query parameter
        redirect_url = reverse(next_url_name) + "?next_url_name=" + "exit_rates"
        return redirect(redirect_url)


@login_required
def transition_rates(request):
    if "session_scenario_id" in request.session:
        pk = request.session["session_scenario_id"]
        session_scenario = get_object_or_404(SessionScenario, pk=pk)
        # read data
        datacontainer = read_data(source=settings.DATA_SOURCE)

        historic_data = apply_filters(
            datacontainer.enriched_view, session_scenario.historic_filters
        )

        # Call predict function
        prediction = predict(
            data=historic_data, **session_scenario.prediction_parameters
        )

        transition_rates = transition_rate_table(prediction.transition_rates)

        if request.method == "POST":
            form = DynamicForm(
                request.POST,
                dataframe=prediction.transition_rates,
                initial_data=session_scenario.adjusted_rates,
            )
            if form.is_valid():
                data = form.save()

                if session_scenario.adjusted_rates is not None:
                    # if previous rate adjustments have been made, update old series with new adjustments
                    rate_adjustments = session_scenario.adjusted_rates
                    new_rates = data.combine_first(rate_adjustments)

                    session_scenario.adjusted_rates = new_rates
                    session_scenario.save()

                else:
                    # Check that the dataframe or series saved in the form is not empty, then save
                    save_data_if_not_empty(session_scenario, data, "adjusted_rates")

                stats = PopulationStats(historic_data)

                adjusted_prediction = predict(
                    data=historic_data,
                    **session_scenario.prediction_parameters,
                    rate_adjustment=session_scenario.adjusted_rates,
                    number_adjustment=session_scenario.adjusted_numbers,
                )

                # build chart
                chart = compare_forecast(
                    stats,
                    prediction,
                    adjusted_prediction,
                    **session_scenario.prediction_parameters,
                )

                is_post = True

                return render(
                    request,
                    "dm_regional_app/views/transition_rates.html",
                    {
                        "transition_rate_table": transition_rates,
                        "form": form,
                        "chart": chart,
                        "is_post": is_post,
                    },
                )

            else:
                form = DynamicForm(
                    request.POST,
                    initial_data=session_scenario.adjusted_rates,
                    dataframe=prediction.transition_rates,
                )

                is_post = False
                messages.warning(request, "Form not saved, positive numbers only")

            return render(
                request,
                "dm_regional_app/views/transition_rates.html",
                {
                    "transition_rate_table": transition_rates,
                    "form": form,
                    "is_post": is_post,
                },
            )

        else:
            form = DynamicForm(
                initial_data=session_scenario.adjusted_rates,
                dataframe=prediction.transition_rates,
            )

            is_post = False

        return render(
            request,
            "dm_regional_app/views/transition_rates.html",
            {
                "transition_rate_table": transition_rates,
                "form": form,
                "is_post": is_post,
            },
        )
    else:
        next_url_name = "router_handler"
        # Construct the URL for the router handler view and append the next_url_name as a query parameter
        redirect_url = reverse(next_url_name) + "?next_url_name=" + "transition_rates"
        return redirect(redirect_url)


@login_required
def adjusted(request):
    if "session_scenario_id" in request.session:
        pk = request.session["session_scenario_id"]
        session_scenario = get_object_or_404(SessionScenario, pk=pk)
        # read data
        datacontainer = read_data(source=settings.DATA_SOURCE)

        if request.method == "POST":
            # check if it was historic data filter form that was submitted
            if "uasc" in request.POST:
                historic_form = HistoricDataFilter(
                    request.POST,
                    la=datacontainer.unique_las,
                    ethnicity=datacontainer.unique_ethnicity,
                )
                predict_form = PredictFilter(
                    initial=session_scenario.prediction_parameters,
                    start_date=datacontainer.start_date,
                    end_date=datacontainer.end_date,
                )
                if historic_form.is_valid():
                    session_scenario.historic_filters = historic_form.cleaned_data
                    session_scenario.save()

                    historic_data = apply_filters(
                        datacontainer.enriched_view, historic_form.cleaned_data
                    )

            # check if it was predict filter form that was submitted
            if "reference_start_date" in request.POST:
                predict_form = PredictFilter(
                    request.POST,
                    start_date=datacontainer.start_date,
                    end_date=datacontainer.end_date,
                )
                historic_form = HistoricDataFilter(
                    initial=session_scenario.historic_filters,
                    la=datacontainer.unique_las,
                    ethnicity=datacontainer.unique_ethnicity,
                )

                historic_data = apply_filters(
                    datacontainer.enriched_view, historic_form.initial
                )
                if predict_form.is_valid():
                    session_scenario.prediction_parameters = predict_form.cleaned_data
                    session_scenario.save()

        else:
            historic_form = HistoricDataFilter(
                initial=session_scenario.historic_filters,
                la=datacontainer.unique_las,
                ethnicity=datacontainer.unique_ethnicity,
            )
            historic_data = apply_filters(
                datacontainer.enriched_view, historic_form.initial
            )

            # initialize form with default dates
            predict_form = PredictFilter(
                initial=session_scenario.prediction_parameters,
                start_date=datacontainer.start_date,
                end_date=datacontainer.end_date,
            )

        if historic_data.empty:
            empty_dataframe = True
            chart = None

            transition_rates = None

            exit_rates = None

            entry_rates = None

        else:
            empty_dataframe = False

            stats = PopulationStats(historic_data)

            original_prediction = predict(
                data=historic_data, **session_scenario.prediction_parameters
            )

            if (
                session_scenario.adjusted_numbers is not None
                or session_scenario.adjusted_rates is not None
            ):
                stats = PopulationStats(historic_data)

                adjusted_prediction = predict(
                    data=historic_data,
                    **session_scenario.prediction_parameters,
                    rate_adjustment=session_scenario.adjusted_rates,
                    number_adjustment=session_scenario.adjusted_numbers,
                )

                # build chart
                chart = compare_forecast(
                    stats,
                    original_prediction,
                    adjusted_prediction,
                    **session_scenario.prediction_parameters,
                )

                current_prediction = adjusted_prediction

            else:
                # build chart
                chart = prediction_chart(
                    stats, original_prediction, **session_scenario.prediction_parameters
                )

                current_prediction = original_prediction

            transition_rates = transition_rate_table(
                current_prediction.transition_rates
            )

            exit_rates = exit_rate_table(current_prediction.transition_rates)

            entry_rates = entry_rate_table(current_prediction.entry_rates)

        return render(
            request,
            "dm_regional_app/views/adjusted.html",
            {
                "predict_form": predict_form,
                "historic_form": historic_form,
                "chart": chart,
                "empty_dataframe": empty_dataframe,
                "transition_rate_table": transition_rates,
                "exit_rate_table": exit_rates,
                "entry_rate_table": entry_rates,
            },
        )
    else:
        next_url_name = "router_handler"
        # Construct the URL for the router handler view and append the next_url_name as a query parameter
        redirect_url = reverse(next_url_name) + "?next_url_name=" + "adjusted"
        return redirect(redirect_url)


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
                    ethnicity=datacontainer.unique_ethnicity,
                )
                predict_form = PredictFilter(
                    initial=session_scenario.prediction_parameters,
                    start_date=datacontainer.start_date,
                    end_date=datacontainer.end_date,
                )
                if historic_form.is_valid():
                    session_scenario.historic_filters = historic_form.cleaned_data
                    session_scenario.save()

                    historic_data = apply_filters(
                        datacontainer.enriched_view, historic_form.cleaned_data
                    )

            if "reference_start_date" in request.POST:
                predict_form = PredictFilter(
                    request.POST,
                    start_date=datacontainer.start_date,
                    end_date=datacontainer.end_date,
                )
                historic_form = HistoricDataFilter(
                    initial=session_scenario.historic_filters,
                    la=datacontainer.unique_las,
                    ethnicity=datacontainer.unique_ethnicity,
                )

                historic_data = apply_filters(
                    datacontainer.enriched_view, historic_form.initial
                )
                if predict_form.is_valid():
                    session_scenario.prediction_parameters = predict_form.cleaned_data
                    session_scenario.save()

        else:
            historic_form = HistoricDataFilter(
                initial=session_scenario.historic_filters,
                la=datacontainer.unique_las,
                ethnicity=datacontainer.unique_ethnicity,
            )
            historic_data = apply_filters(
                datacontainer.enriched_view, historic_form.initial
            )

            # initialize form with default dates
            predict_form = PredictFilter(
                initial=session_scenario.prediction_parameters,
                start_date=datacontainer.start_date,
                end_date=datacontainer.end_date,
            )

        if historic_data.empty:
            empty_dataframe = True
            chart = None

        else:
            empty_dataframe = False

            stats = PopulationStats(historic_data)

            # Call predict function with default dates
            prediction = predict(
                data=historic_data, **session_scenario.prediction_parameters
            )

            # build chart
            chart = prediction_chart(
                stats, prediction, **session_scenario.prediction_parameters
            )

        return render(
            request,
            "dm_regional_app/views/prediction.html",
            {
                "predict_form": predict_form,
                "historic_form": historic_form,
                "chart": chart,
                "empty_dataframe": empty_dataframe,
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
        # read data
        datacontainer = read_data(source=settings.DATA_SOURCE)

        if request.method == "POST":
            # initialize form with data
            form = HistoricDataFilter(
                request.POST,
                la=datacontainer.unique_las,
                ethnicity=datacontainer.unique_ethnicity,
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
                ethnicity=datacontainer.unique_ethnicity,
            )
            data = apply_filters(datacontainer.enriched_view, form.initial)

        entry_into_care_count = data.loc[
            data.placement_type_before == PlacementCategories.NOT_IN_CARE.value.label
        ]["CHILD"].nunique()
        exiting_care_count = data.loc[
            data.placement_type_after == PlacementCategories.NOT_IN_CARE.value.label
        ]["CHILD"].nunique()

        stats = PopulationStats(data)

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
    user_la = request.user.profile.la

    scenarios = SavedScenario.objects.filter(user__profile__la=user_la)

    filterset = SavedScenarioFilter(request.GET, queryset=scenarios)
    filtered_scenarios = filterset.qs

    # Check for the presence of filters
    if not request.GET or not any(request.GET.values()):
        # No filters applied, or query parameters are empty or invalid
        filtered_scenarios = scenarios
    else:
        # Apply filters if they are present and valid
        filtered_scenarios = filterset.qs

    table = SavedScenarioTable(filtered_scenarios)
    RequestConfig(request, paginate={"per_page": 10}).configure(table)

    return render(
        request,
        "dm_regional_app/views/scenarios.html",
        {
            "scenarios": scenarios,
            "table": table,
            "filter": filterset,
        },
    )


@login_required
def scenario_detail(request, pk):
    scenario = get_object_or_404(SavedScenario, pk=pk, user=request.user)
    return render(
        request, "dm_regional_app/views/scenario_detail.html", {"scenario": scenario}
    )


def validate_with_prediction(files):
    """Validate files creating a prediction."""
    try:
        datacontainer = read_local_data(files)
        predict(
            data=datacontainer.enriched_view,
            reference_start_date=datacontainer.start_date,
            reference_end_date=datacontainer.end_date,
        )
    except ValueError:
        return False, "At least one file is invalid."
    else:
        return True, "Successful prediction created."


@user_is_admin
def upload_data_source(request):
    """Allow staff users to upload data.

    3 files must be uploaded: `episodes`, `header`, and `uasc`. Files must be of type `.csv`.
    A prediction will be run to validate the files. If the prediction fails, the files will
    not be successfully uploaded.
    """
    form = DataSourceUploadForm(request.POST or None, request.FILES or None)
    uploads = DataSource.objects.select_related("uploaded_by").order_by("-uploaded")[
        :10
    ]
    if request.method == "POST":
        if form.is_valid():
            files = [files for files in request.FILES.values()]
            success, msg = validate_with_prediction(files)
            if success:
                DataSource.objects.create(uploaded_by=request.user)
                for filename, file in request.FILES.items():
                    full_path = Path(settings.DATA_SOURCE, f"{filename}.csv")
                    # Overwrite files if they already exist
                    if default_storage.exists(full_path):
                        default_storage.delete(full_path)
                    default_storage.save(full_path, file)
                messages.success(request, "Data uploaded successfully")
            else:
                messages.error(request, f"Data not uploaded successfully: {msg}")
            return redirect("upload_data")
    return render(
        request,
        "dm_regional_app/views/upload_data_source.html",
        {"form": form, "uploads": uploads},
    )
