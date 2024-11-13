from allauth.account.views import PasswordChangeView
from django.urls import reverse


class RedirectAfterPasswordChangeView(PasswordChangeView):
    @property
    def success_url(self):
        return reverse("home")
