from django.apps import AppConfig


class DmRegionalAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "dm_regional_app"

    def load_fixtures(self, *args, **kwargs):
        from .fixtures import fixtures

        fixtures()

    def ready(self):
        import dm_regional_app.signals
