from dm_regional_app.builder import Builder
from ssda903 import data


def fixtures():
    builder = Builder()
    user = builder.user(
        first_name="John",
        last_name="Smith",
        email="john.smith@bromley.gov.uk",
        password="test",
    )
    superuser = builder.user(
        first_name="Admin",
        last_name="User",
        email="admin@example.test",
        password="test",
        superuser=True,
    )
    user2 = builder.user(
        first_name="Annie",
        last_name="Smith",
        email="annie.smith@bromley.gov.uk",
        password="test",
    )
    user3 = builder.user(
        first_name="John",
        last_name="Smith",
        email="john.smith@southwark.gov.uk",
        password="test",
    )
