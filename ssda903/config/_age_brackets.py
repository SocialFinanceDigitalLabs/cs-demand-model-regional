import logging
from enum import Enum
from typing import Any, Dict, Optional, Tuple

from ._placement_categories import PlacementCategories

logger = logging.getLogger(__name__)


class AgeBrackets(Enum):
    def __init__(self, config):
        PlacementCategories = config.get("placement_categories", [])
        logger.debug("Configuring AgeBracket with %s", config)

        self.__index = config["index"]
        self.__start = config.get("min", -1)
        self.__end = config.get("max", 30)
        self.__label = config.get("label", f"{self.start} to {self.end}")
        self.__length_in_days = config.get(
            "length_in_days", (self.end - self.start) * 365
        )
        self.__placement_categories = tuple(
            [PlacementCategories[cat] for cat in config.get("categories", [])]
            + [PlacementCategories.OTHER]
        )
        self.__index = config.get("index", 0)
        self._value_ = self.__label

    @property
    def start(self) -> int:
        return self.__start

    @property
    def end(self) -> int:
        return self.__end

    @property
    def placement_categories(self) -> Tuple[PlacementCategories]:
        return self.__placement_categories

    @property
    def label(self):
        return self.__label

    @property
    def index(self):
        return self.__index

    @property
    def next(self):
        return type(self).for_index(self.index + 1)

    @property
    def previous(self):
        return type(self).for_index(self.index - 1)

    @property
    def length_in_days(self):
        return self.__length_in_days

    @property
    def daily_probability(self):
        return 1 / self.length_in_days

    @classmethod
    def bracket_for_age(cls, age: float) -> Optional["AgeBrackets"]:
        for bracket in cls:
            if bracket.start <= age < bracket.end:
                return bracket
        return None

    @classmethod
    def for_index(cls, index: int) -> Optional["AgeBrackets"]:
        for bracket in cls:
            if bracket.index == index:
                return bracket
        return None

    def __str__(self):
        return self.label

    def __repr__(self):
        return f"<{self.__class__.__name__}.{self.name}: {self.label}>"

    def __lt__(self, other):
        return self.__index < other.__index


def build_age_brackets(config: Dict[str, Any], placement_categories=None):
    config = config.copy()
    for ix, v in enumerate(config.values()):
        v["index"] = ix
        if placement_categories:
            v["placement_categories"] = placement_categories

    return AgeBrackets("AgeBrackets", config)
