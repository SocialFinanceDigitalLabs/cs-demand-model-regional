import unittest

from ssda903.config._age_brackets import AgeBracket, AgeBrackets


class AgeBracketTestCase(unittest.TestCase):
    def test_length_in_days(self):
        age_bracket = AgeBracket(start=1, end=5, index=1)
        self.assertEqual(age_bracket.length_in_days, 1460)

    def test_label(self):
        age_bracket = AgeBracket(start=1, end=5, index=1)
        self.assertEqual(age_bracket.label, "1 to 5")

    def test_daily_probability(self):
        age_bracket = AgeBracket(start=1, end=5, index=1)
        self.assertAlmostEqual(age_bracket.daily_probability, 0.0006849315068493151)


class AgeBracketsTestCase(unittest.TestCase):
    def test_values(self):
        expected_values = [
            AgeBracket(_label="Birth to 1", end=1, index=0, _length_in_days=365),
            AgeBracket(start=1, end=5, index=1),
            AgeBracket(start=5, end=10, index=2),
            AgeBracket(start=10, end=16, index=3),
            AgeBracket(_label="16 to 18+", start=16, index=4),
        ]
        self.assertEqual(AgeBrackets.values(), expected_values)

    def test_next(self):
        self.assertEqual(AgeBrackets.BIRTH_TO_ONE.next, AgeBrackets.ONE_TO_FIVE)
        self.assertEqual(AgeBrackets.ONE_TO_FIVE.next, AgeBrackets.FIVE_TO_TEN)
        self.assertEqual(AgeBrackets.FIVE_TO_TEN.next, AgeBrackets.TEN_TO_SIXTEEN)
        self.assertEqual(
            AgeBrackets.TEN_TO_SIXTEEN.next, AgeBrackets.SIXTEEN_TO_EIGHTEEN
        )
        self.assertIsNone(AgeBrackets.SIXTEEN_TO_EIGHTEEN.next)

    def test_previous(self):
        self.assertIsNone(AgeBrackets.BIRTH_TO_ONE.previous)
        self.assertEqual(AgeBrackets.ONE_TO_FIVE.previous, AgeBrackets.BIRTH_TO_ONE)
        self.assertEqual(AgeBrackets.FIVE_TO_TEN.previous, AgeBrackets.ONE_TO_FIVE)
        self.assertEqual(AgeBrackets.TEN_TO_SIXTEEN.previous, AgeBrackets.FIVE_TO_TEN)
        self.assertEqual(
            AgeBrackets.SIXTEEN_TO_EIGHTEEN.previous, AgeBrackets.TEN_TO_SIXTEEN
        )

    def test_bracket_for_age(self):
        self.assertEqual(
            AgeBrackets.bracket_for_age(0.5), AgeBrackets.BIRTH_TO_ONE.value
        )
        self.assertEqual(
            AgeBrackets.bracket_for_age(1.5), AgeBrackets.ONE_TO_FIVE.value
        )
        self.assertEqual(
            AgeBrackets.bracket_for_age(5.5), AgeBrackets.FIVE_TO_TEN.value
        )
        self.assertEqual(
            AgeBrackets.bracket_for_age(10.5), AgeBrackets.TEN_TO_SIXTEEN.value
        )
        self.assertEqual(
            AgeBrackets.bracket_for_age(16.5), AgeBrackets.SIXTEEN_TO_EIGHTEEN.value
        )
        self.assertIsNone(AgeBrackets.bracket_for_age(50))
