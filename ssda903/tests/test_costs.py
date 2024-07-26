import unittest

from ssda903.config._costs import Costs
from ssda903.config._placement_categories import PlacementCategories


class TestCosts(unittest.TestCase):
    def test_cost_item_to_json(self):
        cost_item = Costs.FOSTER_FRIEND_RELATION.value
        expected_json = {
            "label": "Fostering (Friend/Relative)",
            "category": {
                "label": "Fostering",
            },
            "defaults": {
                "cost_per_day": 100,
                "proportion": 0.3,
            },
        }
        self.assertEqual(cost_item.toJSON(), expected_json)

    def test_by_category(self):
        foster_costs = list(Costs.by_category(PlacementCategories.FOSTERING.value))
        expected_foster_costs = [
            Costs.FOSTER_FRIEND_RELATION,
            Costs.FOSTER_IN_HOUSE,
            Costs.FOSTER_IFA,
        ]
        self.assertEqual(foster_costs, expected_foster_costs)
