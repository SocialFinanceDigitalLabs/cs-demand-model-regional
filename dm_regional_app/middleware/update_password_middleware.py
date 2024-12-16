import re

from django.shortcuts import redirect


class UpdatePasswordMiddleware:
    """
    This middleware will check if a user needs to update their password and redirect them
    accordingly. If the user's account is not using SSO and this is their first time logging
    in to the application, then they must change their password.
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
            and current_user.force_password_update
        ):
            # If the user is not using SSO and this is their first time logging in, redirect to change password
            return redirect("account_change_password")

        return self.get_response(request)
