import sys

from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = "Removes all data and creates default fixtures in the database."

    def add_arguments(self, parser):
        parser.add_argument(
            "--noinput",
            action="store_false",
            dest="interactive",
            help="Suppresses all user prompts",
        )

    @transaction.atomic
    def handle(self, *args, interactive=True, **options):
        # Wipe the database
        call_command("flush", interactive=interactive)
        # Load the fixtures
        for config in apps.get_app_configs():
            if hasattr(config, "load_fixtures"):
                config.load_fixtures()
