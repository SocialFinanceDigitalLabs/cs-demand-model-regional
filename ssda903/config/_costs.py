from dataclasses import dataclass
from enum import Enum
from typing import Generator

from ssda903.config._placement_categories import PlacementCategories, PlacementCategory


@dataclass
class CostDefaults:
    cost_per_day: int
    proportion: int


@dataclass
class CostItem:
    label: str
    category: PlacementCategory
    placement_types: tuple
    place_provider: tuple
    defaults: CostDefaults

    def toJSON(self) -> dict:
        return {
            "label": self.label,
            "category": {
                "label": self.category.label,
            },
            "defaults": {
                "cost_per_day": self.defaults.cost_per_day,
                "proportion": self.defaults.proportion,
            },
        }


class Costs(Enum):
    FOSTER_FRIEND_RELATION = CostItem(
        label="Fostering (Friend/Relative)",
        category=PlacementCategories.FOSTERING.value,
        placement_types=(
            "U1",
            "U2",
            "U3",
        ),
        place_provider=(),
        defaults=CostDefaults(cost_per_day=100, proportion=1),
    )
    FOSTER_IN_HOUSE = CostItem(
        label="Fostering (In-house)",
        category=PlacementCategories.FOSTERING.value,
        placement_types=(
            "U4",
            "U5",
            "U6",
        ),
        place_provider=(
            "PR1",
            "PR2",
            "PR3",
        ),
        defaults=CostDefaults(cost_per_day=150, proportion=1),
    )
    FOSTER_IFA = CostItem(
        label="Fostering (IFA)",
        category=PlacementCategories.FOSTERING.value,
        placement_types=(
            "U4",
            "U5",
            "U6",
        ),
        place_provider=("PR4", "PR5"),
        defaults=CostDefaults(cost_per_day=250, proportion=1),
    )
    RESIDENTIAL_IN_HOUSE = CostItem(
        label="Residential (In-house)",
        category=PlacementCategories.RESIDENTIAL.value,
        placement_types=(
            "K2",
            "R1",
            "P3",
            "S1",
        ),
        place_provider=(
            "PR1",
            "PR2",
            "PR3",
        ),
        defaults=CostDefaults(cost_per_day=1000, proportion=1),
    )
    RESIDENTIAL_EXTERNAL = CostItem(
        label="Residential (External)",
        category=PlacementCategories.RESIDENTIAL.value,
        placement_types=(
            "K2",
            "R1",
            "P3",
            "S1",
        ),
        place_provider=("PR4", "PR5"),
        defaults=CostDefaults(cost_per_day=1000, proportion=1),
    )
    SUPPORTED = CostItem(
        label="Supported accomodation",
        category=PlacementCategories.SUPPORTED.value,
        placement_types=(
            "H5",
            "P2",
        ),
        place_provider=(),
        defaults=CostDefaults(cost_per_day=1000, proportion=1),
    )
    SECURE_HOME = CostItem(
        label="Secure home",
        category=PlacementCategories.OTHER.value,  # @Michael note - on 903 guidance this is under residential?
        placement_types=("K1",),
        place_provider=(),
        defaults=CostDefaults(cost_per_day=1000, proportion=1),
    )
    PLACED_WITH_FAMILY = CostItem(
        label="Placed with family",  # M note - used placed with parents code
        category=PlacementCategories.OTHER.value,
        placement_types=("P1",),
        place_provider=(),
        defaults=CostDefaults(cost_per_day=1000, proportion=1),
    )
    OTHER = CostItem(
        label="Other",
        category=PlacementCategories.OTHER.value,
        placement_types=(),
        place_provider=(),
        defaults=CostDefaults(cost_per_day=1000, proportion=1),
    )

    @classmethod
    def by_category(
        cls, category: "PlacementCategory"
    ) -> Generator[CostItem, None, None]:
        for cost in cls:
            if cost.value.category == category:
                yield cost

    @classmethod
    def values(cls) -> list[CostItem]:
        return [a.value for a in cls._members_by_category()]

    @classmethod
    def _members_by_category(cls) -> list["Costs"]:
        """
        Returns a list of all members of the enum ordered by category.
        """
        return sorted(list(cls.__members__.values()), key=lambda x: x.value.category)

    @classmethod
    def get_placement_type_map(cls) -> dict[str, CostItem]:
        """
        Returns a dictionary mapping (placement_type, provider) to PlacementCategory.
        For example:
        {
            ("K2", "PR1"): <PlacementCategory: Residential>,
            ("K2", "PR2"): <PlacementCategory: Residential>,
            ("U1", "PR3"): <PlacementCategory: Fostering>,
            ...
        }
        """
        placement_type_map = {}

        for c in cls.values():
            for placement_type in c.placement_types:
                if c.place_provider:
                    # Create entries for each specific provider
                    for provider in c.place_provider:
                        placement_type_map[(placement_type, provider)] = c
                else:
                    # Create a generic entry that matches any provider
                    placement_type_map[
                        (placement_type, "")
                    ] = c  # Empty string indicates match any provider

        return placement_type_map
