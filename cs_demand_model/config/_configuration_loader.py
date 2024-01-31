from pathlib import Path
from typing import Callable, NamedTuple

import pandas as pd
import yaml

from ..fixtures import config as config_fixtures
from ._age_brackets import AgeBrackets, build_age_brackets
from ._configuration_source import ConfigurationSource
from ._costs import Costs
from ._placement_categories import PlacementCategories, build_placement_categories

DEFAULT_CONFIG_PATH = Path(config_fixtures.__file__).parent / "standard-v1.yaml"


class State(NamedTuple):
    age_bin: AgeBrackets
    placement_type: PlacementCategories


class Transition(NamedTuple):
    age_bin: AgeBrackets
    placement_type: PlacementCategories
    placement_type_after: PlacementCategories


def multi_index(source):
    source = list(source)
    if len(source) == 0:
        raise ValueError("No data to index")
    return pd.MultiIndex.from_tuples(source, names=source[0]._fields)


def supports_index(func: Callable) -> Callable:
    def wrapper(self, *args, **kwargs):
        as_index = kwargs.pop("as_index", False)
        if as_index:
            return multi_index(func(self, *args, **kwargs))
        else:
            return func(self, *args, **kwargs)

    return wrapper


class ConfigMeta(type):
    """
    We create proxy properties for the attributes of the ConfigurationSource, just to make access a bit easier.
    """

    def __new__(mcs, name, bases, dct):
        for key in ["name", "description", "version", "year_in_days", "src"]:
            dct[key] = property(lambda self, k=key: getattr(self._config, k))
        x = super().__new__(mcs, name, bases, dct)
        return x


class Config(metaclass=ConfigMeta):
    def __init__(self, src: str = DEFAULT_CONFIG_PATH):
        with open(src, "rt") as file:
            config = yaml.safe_load(file)

        self._config = ConfigurationSource(config)
        self._placements_categories = build_placement_categories(
            self._config.placement_categories
        )
        self._age_brackets = build_age_brackets(
            self._config.age_brackets, self._placements_categories
        )
        self._costs = Costs(self)

    @property
    def config(self):
        return self._config

    @property
    def costs(self):
        return self._costs

    @property
    def AgeBrackets(self) -> AgeBrackets:
        return self._age_brackets

    @property
    def PlacementCategories(self) -> PlacementCategories:
        return self._placements_categories

    @supports_index
    def states(self) -> State:
        for age_bin in self.AgeBrackets:
            categories = age_bin.placement_categories
            for pt1 in categories:
                yield State(age_bin, pt1)

    @supports_index
    def transitions(
        self, not_in_care=False, self_transitions=True, other_transitions=True
    ) -> Transition:
        for age_bin in self.AgeBrackets:
            from_categories = to_categories = age_bin.placement_categories
            if not_in_care:
                to_categories = to_categories + (self.PlacementCategories.NOT_IN_CARE,)
            for pt1 in from_categories:
                for pt2 in to_categories:
                    if (pt1 == pt2 and self_transitions) or (
                        pt1 != pt2 and other_transitions
                    ):
                        yield Transition(age_bin, pt1, pt2)
