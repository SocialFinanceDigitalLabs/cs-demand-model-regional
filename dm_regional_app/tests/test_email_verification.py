from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.test import TestCase, modify_settings, override_settings
from django.urls import reverse

from dm_regional_app.builder import Builder

User = get_user_model()


@override_settings(
    ACCOUNT_EMAIL_VERIFICATION="mandatory",
    ACCOUNT_EMAIL_VERIFICATION_BY_CODE_ENABLED=True,
    ACCOUNT_RATE_LIMITS={"login_failed": "100/m/ip,500/5m/key", "login": "100/m/ip"},
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)
@modify_settings(
    MIDDLEWARE={
        "remove": [
            "dm_regional_app.middleware.force_mfa_middleware.ForceMFAMiddleware",
            "dm_regional_app.middleware.update_password_middleware.UpdatePasswordMiddleware",
        ]
    }
)
class EmailVerificationTestCase(TestCase):
    builder = Builder()

    def setUp(self):
        mail.outbox = []
        self.client = self.client_class()
        self.user = self.builder.user(email="test@example.com", password="testpass123")

        self.email_address = EmailAddress.objects.create(
            user=self.user, email=self.user.email, verified=False, primary=True
        )
        mail.outbox = []

    def tearDown(self):
        # Django-allauth uses the cache to store email verification codes
        cache.clear()

    def test_send_verification_code(self):
        self.client.post(
            reverse("account_login"),
            {
                "login": "test@example.com",
                "password": "testpass123",
            },
            follow=True,
        )

        self.assertEqual(len(mail.outbox), 1)

    def test_redirect_to_verification_after_login(self):
        response = self.client.post(
            reverse("account_login"),
            {
                "login": "test@example.com",
                "password": "testpass123",
            },
            follow=True,
        )
        self.assertRedirects(response, "/accounts/confirm-email/")

    def test_invalid_code_fails(self):
        self.client.post(
            reverse("account_login"),
            {
                "login": "test@example.com",
                "password": "testpass123",
            },
            follow=True,
        )
        invalid_key = "invalid-key"
        response = self.client.post("/accounts/confirm-email/", {"code": invalid_key})
        self.assertContains(response, "Incorrect code")

    def test_access_allowed_after_verification(self):
        self.email_address.verified = True
        self.email_address.save()
        self.client.post(
            reverse("account_login"),
            {
                "login": "test@example.com",
                "password": "testpass123",
            },
            follow=True,
        )
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
