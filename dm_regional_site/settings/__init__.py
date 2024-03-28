from decouple import config

DJANGO_ENV = config("DJANGO_ENV", default="production")

if DJANGO_ENV == "development":
    from .development import *  # NOQA

elif DJANGO_ENV == "github_actions":
    from .github_actions import *  # NOQA

else:
    from .production import *  # NOQA
