import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


DEFAULT_START = -1
DEFAULT_END = 30


@dataclass
class AgeBracket:
    index: int
    _name: Optional[str] = None
    start: Optional[int] = DEFAULT_START
    end: Optional[int] = DEFAULT_END
    _length_in_days: Optional[int] = None

    @property
    def length_in_days(self):
        if self._length_in_days is not None:
            return self._length_in_days
        return (self.end - self.start) * 365

    @property
    def name(self):
        if self._name is not None:
            return self._name
        return f"{self.start} to {self.end}"

    @property
    def daily_probability(self):
        return 1 / self.length_in_days

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"<{self.__class__.__name__}: {self.name}>"


class AgeBrackets(Enum):
    """
    Age Brackets Enum.

    to get a age bracket dataclass:
    ab = AgeBrackets.BIRTH_TO_ONE.value
    # ab = <AgeBracket: Birth to 1>


    if you do AgeBrackets.BIRTH_TO_ONE that's actually the Enum member, not the AgeBracket:
    not_ab = AgeBrackets.BIRTH_TO_ONE
    # not_ab = <AgeBrackets.BIRTH_TO_ONE: <AgeBracket: Fostering> != <PlacementCategory: Fostering>


    to get a placement category name:
    pc_name = PlacementCategories.FOSTERING.value.name
    # pc = "Fostering"

    if you do PlacementCategories.FOSTERING.name that's actually the name of the Enum member, not the name of the PlacementCategory:
    not_pc_name = PlacementCategories.FOSTERING.name
    # not_pc_name = "FOSTERING" != "Fostering"

    """

    BIRTH_TO_ONE = AgeBracket(_name="Birth to 1", end=1, index=0, _length_in_days=365)
    ONE_TO_FIVE = AgeBracket(start=1, end=5, index=1)
    FIVE_TO_TEN = AgeBracket(start=5, end=10, index=2)
    TEN_TO_SIXTEEN = AgeBracket(start=10, end=16, index=3)
    SIXTEEN_TO_EIGHTEEN = AgeBracket(_name="16 to 18+", start=16, index=4)

    @classmethod
    def values(cls) -> list[AgeBracket]:
        return [a.value for a in cls._members_by_index()]

    @classmethod
    def _members_by_index(cls) -> list["AgeBrackets"]:
        """
        Returns a list of all members of the enum ordered by index.
        """
        return sorted(list(cls.__members__.values()), key=lambda x: x.value.index)

    @property
    def next(self) -> Optional["AgeBrackets"]:
        """
        Returns the next AgeBrackets in the enum.
        If the current AgeBrackets is the last one, returns None.
        """
        members = self._members_by_index()
        current_index = members.index(self)
        if current_index == len(members) - 1:
            return None
        return members[current_index + 1]

    @property
    def previous(self) -> Optional["AgeBrackets"]:
        """
        Returns the previous AgeBrackets in the enum.
        If the current AgeBrackets is the first one, returns None.
        """
        members = self._members_by_index()
        current_index = members.index(self)
        if current_index == 0:
            return None
        return members[current_index - 1]

    @classmethod
    def bracket_for_age(cls, age: float) -> Optional[AgeBracket]:
        for bracket in cls:
            if bracket.value.start <= age < bracket.value.end:
                return bracket.value
        return None


d = AgeBrackets.BIRTH_TO_ONE.name


print(type(d))
