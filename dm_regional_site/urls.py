from django.contrib import admin
from django.urls import include, path

from accounts.views import RedirectAfterPasswordChangeView

urlpatterns = [
    # Specify custom password change view
    path(
        "accounts/password/change/",
        RedirectAfterPasswordChangeView.as_view(),
        name="account_change_password",
    ),
    path("admin/", admin.site.urls),
    path("", include("dm_regional_app.urls")),
    path("accounts/", include("allauth.urls")),
]
