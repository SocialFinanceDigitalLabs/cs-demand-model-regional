from dm_regional_app.builder import Builder
from ssda903 import data


def fixtures():
    builder = Builder()
    user = builder.user(
        first_name="John",
        last_name="Smith",
        email="john.smith@example.test",
        password="test",
    )
    superuser = builder.user(
        first_name="Admin",
        last_name="User",
        email="admin@example.test",
        password="test",
        superuser=True,
    )

    builder.scenario(
        name="Scenario 1",
        description="This is a test scenario",
        user=user,
        data={
            "source": "sample://v1.zip",
            "five to ten fostering": 100,
            "five to ten residential": 100,
            "ten to fifteen other": 100,
        },
    )
    builder.scenario(
        name="Scenario 2",
        description="This is another test scenario",
        user=user,
        data={
            "source": "sample://v1.zip",
            "five to ten fostering": 300,
            "five to ten residential": 200,
            "ten to fifteen other": 200,
        },
    )
