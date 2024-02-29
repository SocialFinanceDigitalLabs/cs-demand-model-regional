from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.backends import EmailBackend

User = get_user_model()


class EmailBackendTestCase(TestCase):
    def setUp(self):
        self.backend = EmailBackend()

    def test_authenticate_with_existing_user(self):
        # Create a user with a known email and password
        email = "test@example.com"
        password = "password"
        user = User.objects.create_user(email=email, password=password)

        # Create a request object
        request = self.client.get("/")

        # Call the authenticate method of the backend
        authenticated_user = self.backend.authenticate(
            request, username=email, password=password
        )

        # Assert that the authenticated user is the same as the created user
        self.assertEqual(authenticated_user, user)

    def test_authenticate_with_non_existing_user(self):
        # Create a request object
        request = self.client.get("/")

        # Call the authenticate method of the backend with a non-existing email
        authenticated_user = self.backend.authenticate(
            request, username="nonexisting@example.com", password="password"
        )

        # Assert that the authenticated user is None
        self.assertIsNone(authenticated_user)

    def test_authenticate_with_uppercase_email(self):
        # Create multiple users with the same email
        email = "TeSt@ExAmpLe.com"
        password = "password"
        user = User.objects.create_user(email=email, password=password)

        # Create a request object
        request = self.client.get("/")

        # Call the authenticate method of the backend
        authenticated_user = self.backend.authenticate(
            request, username=email, password=password
        )

        # Assert that the authenticated user is the first user with the given email
        self.assertEqual(authenticated_user, user)
