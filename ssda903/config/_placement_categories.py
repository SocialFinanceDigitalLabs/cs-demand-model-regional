import logging
from enum import Enum, EnumMeta
from typing import Any, Dict

logger = logging.getLogger(__name__)


class PlacementCategoriesMeta(EnumMeta):
    def __new__(mcs, name, bases, dct, **kwargs):
        cls = super().__new__(mcs, name, bases, dct, **kwargs)

        cls.__labels = {p.label: p for p in cls}

        mappings = {t: p for p in cls for t in p.placement_types}
        cls.__placement_type_map = {t: mappings[t] for t in sorted(mappings.keys())}

        return cls

    @property
    def labels(cls):
        return cls.__labels

    @property
    def placement_type_map(cls):
        return cls.__placement_type_map


class PlacementCategories(Enum, metaclass=PlacementCategoriesMeta):
    def __init__(self, config):
        logger.debug("Configuring PlacementCategories with %s", config)

        self.__label = config.get("label", self.name.capitalize())
        self.__placement_types = tuple(config.get("placement_types", []))
        self.__index = config.get("index", 0)
        self._value_ = self.__label

    @property
    def label(self):
        return self.__label

    @property
    def placement_types(self):
        return self.__placement_types

    def __str__(self):
        return self.label

    def __repr__(self):
        return f"<{self.__class__.__name__}.{self.name}: {self.label}>"

    def __lt__(self, other):
        return self.__index < other.__index


def build_placement_categories(config: Dict[str, Any]):
    config = config.copy()
    for ix, v in enumerate(config.values()):
        v["index"] = ix

    if "OTHER" not in config:
        config["OTHER"] = {"label": "Other"}

    if "NOT_IN_CARE" not in config:
        config["NOT_IN_CARE"] = {"label": "Not in care"}

    return PlacementCategories("PlacementCategories", config)
