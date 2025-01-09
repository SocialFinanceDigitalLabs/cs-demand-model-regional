# Generated by Django 4.2.16 on 2024-11-29 11:13

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("dm_regional_app", "0008_datasource_end_date_datasource_start_date"),
    ]

    operations = [
        migrations.RenameField(
            model_name="profile",
            old_name="show_instructions",
            new_name="show_filtering_instructions",
        ),
        migrations.AddField(
            model_name="profile",
            name="show_rate_adjustment_instructions",
            field=models.BooleanField(default=True),
        ),
    ]
