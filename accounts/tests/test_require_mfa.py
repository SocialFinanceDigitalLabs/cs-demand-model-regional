from allauth.mfa.models import Authenticator
from django.test import TestCase, modify_settings
from django.urls import reverse

from dm_regional_app.builder import Builder


# Remove the custom middleware that doesn't apply to this test suite
@modify_settings(
    MIDDLEWARE={
        "remove": "dm_regional_app.middleware.update_password_middleware.UpdatePasswordMiddleware",
    }
)
class RequireMFATestCase(TestCase):
    builder = Builder()

    def setUp(self):
        self.user = self.builder.user(
            email="testuser", password="testpassword", force_password_update=True
        )
        self.client.login(username="testuser", password="testpassword")

    def test_redirect_user_with_no_mfa(self):
        response = self.client.get(reverse("home"))
        self.assertRedirects(response, reverse("mfa_index"))

    def test_no_redirect_after_mfa_activated(self):
        Authenticator.objects.create(
            user=self.user, type=Authenticator.Type.TOTP, data={"name": "Test passkey"}
        )
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)

    def test_socialaccount_no_mfa(self):
        # Mock SSO login - this is set on new SSO user creation
        self.user.set_unusable_password()
        self.user.save()

        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
