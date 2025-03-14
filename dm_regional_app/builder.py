from typing import Optional

from django.contrib.auth import get_user_model
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
        force_password_update: Optional[bool] = False,
        **kwargs,
    ) -> User:
        data = dict(
            first_name=first_name or self.fake.first_name(),
            last_name=last_name or self.fake.last_name(),
            email=email or self.fake.email(),
            password=password or DEFAULT_PASSWORD,
            force_password_update=force_password_update,
        )
        if superuser:
            user = User.objects.create_superuser(**data, **kwargs)
        else:
            user = User.objects.create_user(**data, **kwargs)
        return user

    def scenario(
        self,
        user: Optional[User] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        historic_filters: Optional[str] = None,
        prediction_parameters: Optional[str] = None,
        adjusted_rates: Optional[str] = None,
        adjusted_numbers: Optional[str] = None,
        historic_stock: Optional[str] = None,
        adjusted_costs: Optional[str] = None,
        **kwargs,
    ):
        scenario = SavedScenario.objects.create(
            user=user or self.user(),
            name=name or self.fake.name(),
            description=description or self.fake.text(),
            historic_filters=historic_filters or self.fake.text(),
            prediction_parameters=prediction_parameters or self.fake.text(),
            adjusted_rates=adjusted_rates or self.fake.text(),
            adjusted_numbers=adjusted_numbers or self.fake.text(),
            historic_stock=historic_stock or self.fake.text(),
            adjusted_costs=adjusted_costs or self.fake.text(),
            **kwargs,
        )
        return scenario
