from django.test import TestCase
from django.urls import reverse

from dm_regional_app.builder import Builder


class ScenariosTestCase(TestCase):
    builder = Builder()

    def setUp(self):
        self.user = self.builder.user(
            email="testuser",
            password="testpassword",
        )
        self.client.login(username="testuser", password="testpassword")
        self.scenario = self.builder.scenario(name="Test Scenario", user=self.user)

    def test_scenarios_view(self):
        response = self.client.get(reverse("scenarios"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "dm_regional_app/views/scenarios.html")
        self.assertContains(response, "Test Scenario")
        self.assertQuerysetEqual(response.context["scenarios"], [self.scenario])

    def test_scenarios_view_no_user(self):
        self.client.logout()
        response = self.client.get(reverse("scenarios"))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, "/accounts/login/?next=/scenarios")

    def test_scenarios_view_no_scenarios(self):
        self.scenario.delete()
        response = self.client.get(reverse("scenarios"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "dm_regional_app/views/scenarios.html")
        self.assertQuerysetEqual(response.context["scenarios"], [])

    def test_different_user_only_sees_their_scenarios(self):
        other_user = self.builder.user(
            email="testuser2",
            password="testpassword2",
        )
        other_scenario = self.builder.scenario(name="Test Scenario 2", user=other_user)
        self.client.login(username="testuser2", password="testpassword2")

        response = self.client.get(reverse("scenarios"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "dm_regional_app/views/scenarios.html")
        self.assertQuerysetEqual(response.context["scenarios"], [other_scenario])
