import unittest

from ssda903.config._placement_categories import PlacementCategories, PlacementCategory


class PlacementCategoriesTestCase(unittest.TestCase):
    def test_values(self):
        categories = PlacementCategories.values()
        self.assertIsInstance(categories, list)
        self.assertTrue(
            all(isinstance(category, PlacementCategory) for category in categories)
        )

    def test_members_by_index(self):
        members = PlacementCategories._members_by_index()
        self.assertIsInstance(members, list)
        self.assertTrue(
            all(isinstance(member, PlacementCategories) for member in members)
        )
        self.assertEqual(len(members), len(PlacementCategories))

    def test_get_placement_type_map(self):
        placement_type_map = PlacementCategories.get_placement_type_map()
        self.assertIsInstance(placement_type_map, dict)
        self.assertTrue(
            all(
                isinstance(key, str) and isinstance(value, PlacementCategory)
                for key, value in placement_type_map.items()
            )
        )
