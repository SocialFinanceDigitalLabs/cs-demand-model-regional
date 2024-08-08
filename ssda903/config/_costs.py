from dataclasses import dataclass
from enum import Enum
from typing import Generator

import pandas as pd

from ssda903.config._placement_categories import PlacementCategories, PlacementCategory


@dataclass
class CostDefaults:
    cost_per_week: int
    proportion: int


@dataclass
class CostItem:
    label: str
    category: PlacementCategory
    defaults: CostDefaults

    def toJSON(self) -> dict:
        return {
            "label": self.label,
            "category": {
                "label": self.category.label,
            },
            "defaults": {
                "cost_per_week": self.defaults.cost_per_week,
                "proportion": self.defaults.proportion,
            },
        }


class Costs(Enum):
    FOSTER_FRIEND_RELATION = CostItem(
        label="Fostering (Friend/Relative)",
        category=PlacementCategories.FOSTERING.value,
        defaults=CostDefaults(cost_per_week=100, proportion=0.3),
    )
    FOSTER_IN_HOUSE = CostItem(
        label="Fostering (In-house)",
        category=PlacementCategories.FOSTERING.value,
        defaults=CostDefaults(cost_per_week=150, proportion=0.3),
    )
    FOSTER_IFA = CostItem(
        label="Fostering (IFA)",
        category=PlacementCategories.FOSTERING.value,
        defaults=CostDefaults(cost_per_week=250, proportion=0.4),
    )
    RESIDENTIAL_IN_HOUSE = CostItem(
        label="Residential (In-house)",
        category=PlacementCategories.RESIDENTIAL.value,
        defaults=CostDefaults(cost_per_week=1000, proportion=0.5),
    )
    RESIDENTIAL_EXTERNAL = CostItem(
        label="Residential (External)",
        category=PlacementCategories.RESIDENTIAL.value,
        defaults=CostDefaults(cost_per_week=1000, proportion=0.5),
    )
    SUPPORTED = CostItem(
        label="Supported accomodation",
        category=PlacementCategories.SUPPORTED.value,
        defaults=CostDefaults(cost_per_week=1000, proportion=1),
    )
    SECURE_HOME = CostItem(
        label="Secure home",
        category=PlacementCategories.OTHER.value,
        defaults=CostDefaults(cost_per_week=1000, proportion=0.3),
    )
    PLACED_WITH_FAMILY = CostItem(
        label="Placed with family",
        category=PlacementCategories.OTHER.value,
        defaults=CostDefaults(cost_per_week=1000, proportion=0.3),
    )
    OTHER = CostItem(
        label="Other",
        category=PlacementCategories.OTHER.value,
        defaults=CostDefaults(cost_per_week=1000, proportion=0.4),
    )

    @classmethod
    def by_category(
        cls, category: "PlacementCategory"
    ) -> Generator[CostItem, None, None]:
        for cost in cls:
            if cost.value.category == category:
                yield cost

    @classmethod
    def to_dataframe(cls):
        data = {
            "cost": {
                item.value.label: item.value.defaults.cost_per_week for item in cls
            }
        }
        df = pd.DataFrame(data)
        return df
