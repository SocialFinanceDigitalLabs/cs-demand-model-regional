import re

from allauth.mfa.utils import is_mfa_enabled
from django.shortcuts import redirect


class ForceMFAMiddleware:
    """
    This middleware will check if a user needs to setup MFA and redirect them
    accordingly. If the user is not using SSO, MFA is required.
    """

    PATHS_TO_IGNORE = re.compile(
        r"(/admin.*)|(/accounts/.*)",
        re.IGNORECASE,
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if self.PATHS_TO_IGNORE.match(request.path_info):
            return self.get_response(request)

        current_user = request.user
        if (
            current_user.is_authenticated
            and current_user.has_usable_password()
            and not is_mfa_enabled(current_user)
        ):
            # If the user is not using SSO, they must set up MFA
            return redirect("mfa_index")

        return self.get_response(request)
