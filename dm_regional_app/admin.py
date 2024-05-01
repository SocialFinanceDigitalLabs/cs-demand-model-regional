from django.contrib import admin

from .models import SavedScenario, SessionScenario

admin.site.register(SessionScenario)
admin.site.register(SavedScenario)

# Register your models here.
