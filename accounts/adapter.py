from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from sentry_sdk import capture_exception


class CustomUserAdapter(DefaultAccountAdapter):
    def is_open_for_signup(self, request):
        """Do not allow users to sign up via the standard signup form."""
        return False


class SocialAccountCustomUserAdapter(DefaultSocialAccountAdapter):
    def populate_user(self, request, sociallogin, data):
        user = super().populate_user(request, sociallogin, data)
        user.force_password_update = False
        return user

    def on_authentication_error(
        self,
        request,
        provider,
        error=None,
        exception=None,
        extra_context=None,
    ):
        capture_exception(exception)
