from django.test.runner import DiscoverRunner

from .base import *  # NOQA

# heroku configuration - found on https://github.com/heroku/python-getting-started

# Use WhiteNoise's runserver implementation instead of the Django default, for dev-prod parity.
INSTALLED_APPS = ["whitenoise.runserver_nostatic"] + INSTALLED_APPS

STATIC_ROOT = BASE_DIR / "staticfiles"
STATIC_URL = "static/"
WHITENOISE_KEEP_ONLY_HASHED_FILES = True


STORAGES = {
    # Enable WhiteNoise's GZip and Brotli compression of static assets:
    # https://whitenoise.readthedocs.io/en/latest/django.html#add-compression-and-caching-support
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}
