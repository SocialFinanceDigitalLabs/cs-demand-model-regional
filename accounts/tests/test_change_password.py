from django.test import TestCase, modify_settings
from django.urls import reverse

from dm_regional_app.builder import Builder


# Remove the custom middleware that doesn't apply to this test suite
@modify_settings(
    MIDDLEWARE={
        "append": "dm_regional_app.middleware.update_password_middleware.UpdatePasswordMiddleware",
    }
)
class ChangePasswordTestCase(TestCase):
    builder = Builder()

    def setUp(self):
        self.user = self.builder.user(
            email="testuser", password="testpassword", force_password_update=True
        )
        self.client.login(username="testuser", password="testpassword")

    def test_redirect_new_user(self):
        response = self.client.get(reverse("home"))
        self.assertRedirects(response, reverse("account_change_password"))

    def test_remove_password_update_flag(self):
        data = {
            "oldpassword": "testpassword",
            "password1": "astrongerpassword",
            "password2": "astrongerpassword",
        }
        response = self.client.post(reverse("account_change_password"), data)
        self.assertRedirects(response, reverse("home"))
        self.user.refresh_from_db()
        self.assertFalse(self.user.force_password_update)

    def test_socialaccount_no_password_change(self):
        # Mock SSO login - this is set on new SSO user creation
        self.user.set_unusable_password()
        self.user.save()

        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)

    def test_reset_password_update_flag(self):
        """If a user has their password reset when they were not forced to reset it already
        then this should set the flag to force them to update their password on next login
        """
        data = {
            "oldpassword": "astrongerpassword",
            "password1": "anevenstrongerpassword",
            "password2": "anevenstrongerpassword",
        }
        self.client.post(reverse("account_change_password"), data)
        self.user.refresh_from_db()
        self.assertTrue(self.user.force_password_update)
