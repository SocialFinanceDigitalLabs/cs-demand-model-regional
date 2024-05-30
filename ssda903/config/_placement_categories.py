import logging
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


@dataclass
class PlacementCategory:
    label: str
    placement_types: tuple
    index: int = 0

    def __lt__(self, other: "PlacementCategory"):
        if not isinstance(other, PlacementCategory):
            raise TypeError(
                f"Cannot compare {self.__class__.__name__} with {other.__class__.__name__}"
            )
        return self.index < other.index

    def __str__(self):
        return self.label

    def __repr__(self):
        return f"<{self.__class__.__name__}: {self.label}>"


class PlacementCategories(Enum):
    """
    Placement Categories Enum.

    to get a placement category dataclass:
    pc = PlacementCategories.FOSTERING.value
    pc will be  <PlacementCategory: Fostering>


    if you do PlacementCategories.FOSTERING that's actually the Enum member, not the PlacementCategory:
    not_pc = PlacementCategories.FOSTERING
    not_pc will be <PlacementCategories.FOSTERING: <PlacementCategory: Fostering>
    which is not the same as <PlacementCategory: Fostering>


    to get a placement category label:
    pc_label = PlacementCategories.FOSTERING.value.label
    pc_label will be "Fostering"

    if you do PlacementCategories.FOSTERING.name that's actually the name of the Enum member, not the label of the PlacementCategory:
    not_pc_label = PlacementCategories.FOSTERING.name
    not_pc_label will be "FOSTERING"
    which is not them same as "Fostering"

    """

    FOSTERING = PlacementCategory(
        label="Fostering",
        placement_types=(
            "U1",
            "U2",
            "U3",
            "U4",
            "U5",
            "U6",
        ),
        index=0,
    )

    RESIDENTIAL = PlacementCategory(
        label="Residential",
        placement_types=(
            "K2",
            "R1",
        ),
        index=1,
    )

    SUPPORTED = PlacementCategory(
        label="Supported",
        placement_types=(
            "H5",
            "P2",
        ),
        index=2,
    )
    OTHER = PlacementCategory(
        label="Other",
        placement_types=(),
        index=3,
    )

    NOT_IN_CARE = PlacementCategory(
        label="Not in care",
        placement_types=(),
        index=4,
    )

    @classmethod
    def values(cls) -> list[PlacementCategory]:
        return [a.value for a in cls._members_by_index()]

    @classmethod
    def _members_by_index(cls) -> list["PlacementCategories"]:
        """
        Returns a list of all members of the enum ordered by index.
        """
        return sorted(list(cls.__members__.values()), key=lambda x: x.value.index)

    @classmethod
    def get_placement_type_map(cls) -> dict[str, PlacementCategory]:
        """
        return a dictionary of placement types to placement categories
        for example:
        {
            "U1": <PlacementCategory: Fostering>,
            "U2": <PlacementCategory: Fostering>,
            ...
            "K2": <PlacementCategory: Residential>,
            "R1": <PlacementCategory: Residential>,
            ...
        }
        """
        return {pt: pc for pc in cls.values() for pt in pc.placement_types}
