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
]
