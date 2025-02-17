from django.test import TestCase, modify_settings
from django.urls import reverse

from dm_regional_app.builder import Builder


# Remove the custom middleware that doesn't apply to this test suite
@modify_settings(
    MIDDLEWARE={
        "remove": [
            "dm_regional_app.middleware.scenario_middleware.SessionScenarioMiddleware",
            "dm_regional_app.middleware.force_mfa_middleware.ForceMFAMiddleware",
        ]
    }
)
class ScenarioDetailViewTestCase(TestCase):
    builder = Builder()

    def setUp(self):
        self.user = self.builder.user(
            email="testuser",
            password="testpassword",
        )
        self.client.login(username="testuser", password="testpassword")
        self.scenario = self.builder.scenario(name="Test Scenario", user=self.user)

    def test_scenario_detail(self):
        url = reverse("scenario_detail", args=[self.scenario.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "dm_regional_app/views/scenario_detail.html")
        self.assertEqual(response.context["scenario"], self.scenario)

    def test_scenario_detail_invalid_pk(self):
        invalid_pk = self.scenario.pk + 1
        url = reverse("scenario_detail", args=[invalid_pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_scenario_detail_unauthenticated_user(self):
        self.client.logout()
        url = reverse("scenario_detail", args=[self.scenario.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(
            response, "/accounts/login/?next=/scenario/{}".format(self.scenario.pk)
        )

    def test_scenario_detail_different_user(self):
        self.builder.user(
            email="testuser2",
            password="testpassword2",
        )
        self.client.login(username="testuser2", password="testpassword2")
        url = reverse("scenario_detail", args=[self.scenario.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
