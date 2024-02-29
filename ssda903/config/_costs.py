from dataclasses import dataclass
from typing import Generator


@dataclass
class CostDefaults:
    cost_per_day: int
    proportion: int


@dataclass
class CostItem:
    id: str
    label: str
    category: "PlacementCategory"
    defaults: CostDefaults

    def toJSON(self) -> dict:
        return {
            "id": self.id,
            "label": self.label,
            "category": {
                "name": self.category.name,
                "label": self.category.label,
            },
            "defaults": {
                "cost_per_day": self.defaults.cost_per_day,
                "proportion": self.defaults.proportion,
            },
        }


def _parse_config(config: "Config") -> Generator[CostItem, None, None]:
    for key, value in config.config.costs.items():
        category = config.PlacementCategories[value["category"]]
        defaults = CostDefaults(**value["defaults"])
        yield CostItem(key, value["label"], category, defaults)


class Costs:
    def __init__(self, config: "Config"):
        self.costs = {cost.id: cost for cost in _parse_config(config)}

    def __getitem__(self, key):
        return self.costs[key]

    def by_category(
        self, category: "PlacementCategory"
    ) -> Generator[CostItem, None, None]:
        for cost in self.costs.values():
            if cost.category == category:
                yield cost

    def __iter__(self):
        return iter(self.costs.values())
