from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from sentry_sdk import capture_exception


class CustomUserAdapter(DefaultSocialAccountAdapter):
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
