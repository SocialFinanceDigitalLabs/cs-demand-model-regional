import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional
import pandas as pd

logger = logging.getLogger(__name__)


DEFAULT_START = -1
DEFAULT_END = 30


@dataclass
class AgeBracket:
    index: int
    _label: Optional[str] = None
    start: Optional[int] = DEFAULT_START
    end: Optional[int] = DEFAULT_END
    _length_in_days: Optional[int] = None

    @property
    def length_in_days(self):
        if self._length_in_days is not None:
            return self._length_in_days
        return (self.end - self.start) * 365

    @property
    def label(self):
        if self._label is not None:
            return self._label
        return f"{self.start} to {self.end}"

    @property
    def daily_probability(self):
        return 1 / self.length_in_days

    def __str__(self):
        return self.label

    def __repr__(self):
        return f"<{self.__class__.__name__}: {self.label}>"


class AgeBrackets(Enum):
    """
    Age Brackets Enum.

    to get a age bracket dataclass:
    ab = AgeBrackets.BIRTH_TO_ONE.value
    ab will be <AgeBracket: Birth to 1>


    if you do AgeBrackets.BIRTH_TO_ONE that's actually the Enum member, not the AgeBracket:
    not_ab = AgeBrackets.BIRTH_TO_ONE
    not_ab will be <AgeBrackets.BIRTH_TO_ONE: <AgeBracket: Birth to 1>
    which is not the same as <AgeBracket: Birth to 1>

    to get a age bracket label:
    ab_label = AgeBrackets.BIRTH_TO_ONE.value.label
    ab_label will be "Birth to 1"

    if you do AgeBrackets.BIRTH_TO_ONE.name that's actually the name of the Enum member, not the label of the AgeBracket:
    not_ab_label = AgeBrackets.BIRTH_TO_ONE.name
    not_ab_label will be "BIRTH_TO_ONE"
    which is not the same as "Birth to 1"

    """

    BIRTH_TO_ONE = AgeBracket(_label="Birth to 1", end=1, index=0, _length_in_days=365)
    ONE_TO_FIVE = AgeBracket(start=1, end=5, index=1)
    FIVE_TO_TEN = AgeBracket(start=5, end=10, index=2)
    TEN_TO_SIXTEEN = AgeBracket(start=10, end=16, index=3)
    SIXTEEN_TO_EIGHTEEN = AgeBracket(_label="16 to 18+", start=16, index=4)

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
    
    @classmethod
    def to_dataframe(cls):
        '''
        Convert the Enum into a DataFrame
        '''
        return pd.DataFrame([
            {"start": bracket.value.start, "end": bracket.value.end, "label": bracket.value.label, "index": bracket.value.index}
            for bracket in cls
        ]).sort_values("start").reset_index(drop=True)
