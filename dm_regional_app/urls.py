from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("predict/", views.chart_view, name="chart_view"),
    path("scenario/<int:pk>", views.scenario_detail, name="scenario_detail"),
    path("scenarios", views.scenarios, name="scenarios"),
]
