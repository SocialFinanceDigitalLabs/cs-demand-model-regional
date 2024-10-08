from .base import *  # NOQA

# heroku configuration - found on https://github.com/heroku/python-getting-started

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
