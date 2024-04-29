from typing import Optional

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from faker import Faker

from dm_regional_app.models import SavedScenario

User = get_user_model()
DEFAULT_PASSWORD = "test"


class Builder:
    def __init__(self, seed=100):
        super().__init__()
        Faker.seed(seed)
        self.fake = Faker("en-GB")

    def user(
        self,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        email: Optional[str] = None,
        password: Optional[str] = None,
        superuser: Optional[bool] = False,
        **kwargs,
    ) -> User:
        password = make_password(password or DEFAULT_PASSWORD)
        data = dict(
            first_name=first_name or self.fake.first_name(),
            last_name=last_name or self.fake.last_name(),
            email=email or self.fake.email(),
            password=password,
        )
        if superuser:
            user = User.objects.create_superuser(**data, **kwargs)
        else:
            user = User.objects.create(**data, **kwargs)
        return user

    def scenario(
        self,
        user: Optional[User] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        historic_filters: Optional[str] = None,
        prediction_filters: Optional[str] = None,
        prediction_parameters: Optional[str] = None,
        historic_stock: Optional[str] = None,
        adjusted_costs: Optional[str] = None,
        **kwargs,
    ):
        scenario = SavedScenario.objects.create(
            user=user or self.user(),
            name=name or self.fake.name(),
            description=description or self.fake.text(),
            historic_filters=historic_filters or self.fake.text(),
            prediction_filters=prediction_filters or self.fake.text(),
            prediction_parameters=prediction_parameters or self.fake.text(),
            historic_stock=historic_stock or self.fake.text(),
            adjusted_costs=adjusted_costs or self.fake.text(),
            **kwargs,
        )
        return scenario
