from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("dm_regional_app.urls")),
    path("accounts/", include("allauth.urls")),
]
