"""
Django settings for dm_regional_site project.

Generated by 'django-admin startproject' using Django 4.2.7.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.2/ref/settings/
"""

from pathlib import Path

import dj_database_url
from decouple import config
from django.contrib import messages

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config(
    "DJANGO_SECRET_KEY",
    default="django-insecure-gh4wp!kqd8#nc6_o)eqxs@_4w2+9+p(rq$bdz&d2*!jg946@w3",
)
# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config("DEBUG", default=False, cast=bool)

ALLOWED_HOSTS = config(
    "ALLOWED_HOSTS", cast=lambda v: [s.strip() for s in v.split(",")], default=""
)


# Application definition

INSTALLED_APPS = [
    "accounts",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "dm_regional_app.apps.DmRegionalAppConfig",
    "crispy_forms",
    "crispy_bootstrap5",
    "bootstrap_datepicker_plus",
    "django_select2",
    "django_tables2",
    "sekizai",
    # 3rd Party
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    # Social Providers
    "allauth.socialaccount.providers.microsoft",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "dm_regional_app.middleware.update_password_middleware.UpdatePasswordMiddleware",
    "dm_regional_app.middleware.scenario_middleware.SessionScenarioMiddleware",
]

MICROSOFT_CLIENT_ID = config("MICROSOFT_CLIENT_ID", default="")
MICROSOFT_CLIENT_SECRET = config("MICROSOFT_CLIENT_SECRET", default="")
MICROSOFT_TENANT_ID = config("MICROSOFT_TENANT_ID", default="")
SOCIALACCOUNT_PROVIDERS = {
    "microsoft": {
        "APPS": [
            {
                "client_id": MICROSOFT_CLIENT_ID,
                "secret": MICROSOFT_CLIENT_SECRET,
                "settings": {
                    "tenant": MICROSOFT_TENANT_ID,
                    # Optional: override URLs (use base URLs without path)
                    "login_url": "https://login.microsoftonline.com",
                },
            }
        ]
    }
}

ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_AUTHENTICATION_METHOD = "email"
ACCOUNT_SESSION_REMEMBER = False
ACCOUNT_FORMS = {
    "login": "accounts.forms.CustomLoginForm",
    "change_password": "accounts.forms.CustomChangePasswordForm",
}
SOCIALACCOUNT_ADAPTER = "accounts.adapter.CustomUserAdapter"
ACCOUNT_EMAIL_VERIFICATION = "none"


ROOT_URLCONF = "dm_regional_site.urls"
X_FRAME_OPTIONS = "SAMEORIGIN"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "sekizai.context_processors.sekizai",
            ],
        },
    },
]

AUTH_USER_MODEL = "accounts.CustomUser"


AUTHENTICATION_BACKENDS = (
    "accounts.backends.EmailBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
)


WSGI_APPLICATION = "dm_regional_site.wsgi.application"


# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases
MAX_CONN_AGE = 600
DATABASES = {
    "default": dj_database_url.config(
        default=config("DATABASE_URL", f"sqlite:///{BASE_DIR}/db.sqlite3"),
        conn_max_age=MAX_CONN_AGE,
        ssl_require=False,
    ),
}


# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True

LOGIN_REDIRECT_URL = "home"
LOGOUT_REDIRECT_URL = "home"

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL = "static/"
STATICFILES_DIRS = [
    BASE_DIR / "static",
]
# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# crispy forms
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"


# data source path
DATA_SOURCE = config("DATA_SOURCE", default="samples/v1")

MESSAGE_TAGS = {
    messages.DEBUG: "alert-info",
    messages.INFO: "alert-info",
    messages.SUCCESS: "alert-success",
    messages.WARNING: "alert-warning",
    messages.ERROR: "alert-danger",
}
