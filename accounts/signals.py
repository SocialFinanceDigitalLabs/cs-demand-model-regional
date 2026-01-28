import logging

from django.contrib.admin.models import ACTION_FLAG_CHOICES, LogEntry
from django.contrib.auth.signals import (
    user_logged_in,
    user_logged_out,
    user_login_failed,
)
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

ACTIONS_MAP = {value: name for value, name in ACTION_FLAG_CHOICES}

log_auth = logging.getLogger("security.authentication")
log_admin = logging.getLogger("security.admin")


def get_client_ip(request):
    if not request:
        return None

    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        # Take the original client IP if possible
        return xff.split(",")[0].strip()

    return request.META.get("REMOTE_ADDR")


@receiver(user_logged_in)
def user_logged_in_callback(sender, request, user, **kwargs):
    log_auth.info(
        f"{user.email} login success",
        extra={
            "category": "authentication",
            "event": "login",
            "status": "success",
            "user_id": user.id,
            "user_email": user.email,
            "ip": get_client_ip(request),
        },
    )


@receiver(user_logged_out)
def user_logged_out_callback(sender, request, user, **kwargs):
    log_auth.info(
        f"{user.email} logout success",
        extra={
            "category": "authentication",
            "event": "logout",
            "status": "success",
            "user_id": user.id,
            "user_email": user.email,
            "ip": get_client_ip(request),
        },
    )


@receiver(user_login_failed)
def user_login_failed_callback(sender, credentials, request, **kwargs):
    log_auth.warning(
        f"User login failure: {credentials}",
        extra={
            "category": "authentication",
            "event": "login",
            "status": "failure",
            "credentials": credentials,
            "ip": get_client_ip(request),
        },
    )


@receiver(post_save, sender=LogEntry)
def log_admin_activity(sender, instance, created, **kwargs):
    if not created:
        return

    def emit_log():
        entry = LogEntry.objects.select_related("user").get(pk=instance.pk)

        user_email = entry.user.email if entry.user else None
        log_admin.info(
            f"Admin action taken: {user_email} {instance}",
            extra={
                "category": "admin",
                "event": "admin_action",
                "user_id": entry.user_id,
                "user_email": user_email,
                "action_flag": instance.action_flag,
                "action": ACTIONS_MAP.get(instance.action_flag, "unknown"),
                "content_type": instance.content_type.model
                if instance.content_type
                else None,
                "object_id": instance.object_id,
                "object_repr": entry.object_repr,
                "change": str(instance),
            },
        )

    transaction.on_commit(emit_log)
