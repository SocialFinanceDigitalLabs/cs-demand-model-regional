from django.shortcuts import render

from . import plotly


# Create your views here.
def plotly_view(request):
    return render(request, "dm_regional_app/plotly.html")
