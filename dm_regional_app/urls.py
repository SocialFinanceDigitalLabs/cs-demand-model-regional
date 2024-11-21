from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("predict/", views.prediction, name="prediction"),
    path("scenario/<int:pk>", views.scenario_detail, name="scenario_detail"),
    path("scenarios", views.scenarios, name="scenarios"),
    path("historic_data/", views.historic_data, name="historic_data"),
    path("router_handler", views.router_handler, name="router_handler"),
    path("adjusted", views.adjusted, name="adjusted"),
    path("transition_rates", views.transition_rates, name="transition_rates"),
    path("exit_rates", views.exit_rates, name="exit_rates"),
    path("entry_rates", views.entry_rates, name="entry_rates"),
    path("clear_rates", views.clear_rate_adjustments, name="clear_rates"),
    path("costs", views.costs, name="costs"),
    path("weekly_costs", views.weekly_costs, name="weekly_costs"),
    path(
        "placement_proportions",
        views.placement_proportions,
        name="placement_proportions",
    ),
    path("save_scenario", views.save_scenario, name="save_scenario"),
    path("load_scenario/<int:pk>", views.load_saved_scenario, name="load_scenario"),
    path(
        "clear_proportions",
        views.clear_proportion_adjustments,
        name="clear_proportions",
    ),
    path("upload_data/", views.upload_data_source, name="upload_data"),
    path(
        "update_modal_preference/",
        views.update_modal_preference,
        name="update_modal_preference",
    ),
]
