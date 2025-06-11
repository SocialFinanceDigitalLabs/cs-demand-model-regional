from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect


def user_is_admin(view_func):
    """Decorator to check if the user is an admin and has logged in via SSO."""

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if (
            request.user.is_authenticated
            and request.user.socialaccount_set.exists()
            and request.user.is_active
            and request.user.is_staff
        ):
            return view_func(request, *args, **kwargs)
        messages.error(request, "You must be an admin to upload data.")
        return redirect("home")

    return wrapper
