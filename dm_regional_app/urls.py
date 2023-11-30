from django.urls import path

from . import views

urlpatterns = [
    path("", views.plotly_view, name="plotly_view"),
]
