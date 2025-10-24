import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.types import Event, Hint

from .base import *  # NOQA

# heroku configuration - found on https://github.com/heroku/python-getting-started

SENTRY_DSN = config("SENTRY_DSN", default=None)


def before_send(event: Event, hint: Hint) -> Event | None:
    exception_values = event.get("exception", {}).get("values", [])
    for exception in exception_values:
        stacktrace = exception.get("stacktrace", {})
        frames = stacktrace.get("frames", [])
        for frame in frames:
            # Redact local variables to avoid sending sensitive information to Sentry
            if "vars" in frame:
                frame["vars"] = {k: "<redacted>" for k in frame["vars"].keys()}
    return event


sentry_sdk.init(
    dsn=SENTRY_DSN,
    integrations=[DjangoIntegration()],
    traces_sample_rate=0.1,
    send_default_pii=True,
    before_send=before_send,
)

# Use WhiteNoise's runserver implementation instead of the Django default, for dev-prod parity.
INSTALLED_APPS = ["whitenoise.runserver_nostatic"] + INSTALLED_APPS + ["storages"]

STATIC_ROOT = BASE_DIR / "staticfiles"
STATIC_URL = "static/"
WHITENOISE_KEEP_ONLY_HASHED_FILES = True


STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3.S3Storage",
    },
    # Enable WhiteNoise's GZip and Brotli compression of static assets:
    # https://whitenoise.readthedocs.io/en/latest/django.html#add-compression-and-caching-support
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# Chosen way of AWS authentication - check this link if you want to change how it's done:
# https://django-storages.readthedocs.io/en/latest/backends/amazon-S3.html
AWS_ACCESS_KEY_ID = config("AWS_ACCESS_KEY_ID", default=None)
AWS_SECRET_ACCESS_KEY = config("AWS_SECRET_ACCESS_KEY", default=None)
AWS_STORAGE_BUCKET_NAME = config("AWS_STORAGE_BUCKET_NAME", default=None)

ACCOUNT_EMAIL_VERIFICATION = "mandatory"
ACCOUNT_EMAIL_VERIFICATION_BY_CODE_ENABLED = True
ACCOUNT_EMAIL_VERIFICATION_BY_CODE_TIMEOUT = 60 * 10  # 10 minutes
ACCOUNT_RATE_LIMITS = {"login_failed": "10/m/ip,5/5m/key"}
