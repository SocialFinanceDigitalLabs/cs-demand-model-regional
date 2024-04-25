from django.core.management.base import BaseCommand

from dm_regional_app.models import SessionScenario


class Command(BaseCommand):
    help = "Erases all SessionScenario data weekly"

    def handle(self, *args, **options):
        # Delete all session scenario data. This command is set to run weekly at midnight on Sundays.
        try:
            SessionScenario.objects.all().delete()
            self.stdout.write(self.style.SUCCESS("Data erased successfully."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error: {e}"))
