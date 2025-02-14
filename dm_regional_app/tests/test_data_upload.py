from datetime import datetime
from unittest import mock
from unittest.mock import MagicMock, patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, modify_settings
from django.urls import reverse

from dm_regional_app.builder import Builder
from dm_regional_app.forms import DataSourceUploadForm
from dm_regional_app.models import DataSource


# Remove the custom middleware that doesn't apply to this test suite
@modify_settings(
    MIDDLEWARE={
        "remove": "dm_regional_app.middleware.force_mfa_middleware.ForceMFAMiddleware"
    }
)
class DataUploadTestCase(TestCase):
    builder = Builder()

    def setUp(self):
        self.user = self.builder.user(
            email="testuser",
            password="testpassword",
        )
        self.client.login(username="testuser", password="testpassword")
        self.user.is_staff = True
        self.user.save()
        # Mock SSO login
        self.user.socialaccount_set.create()

    def tearDown(self):
        DataSource.objects.all().delete()

    def test_authenticated_user(self):
        response = self.client.get(reverse("upload_data"))
        self.assertEqual(response.status_code, 200)

    def test_nonauthenticated_user(self):
        self.user.is_staff = False
        self.user.save()
        response = self.client.get(reverse("upload_data"))
        self.assertRedirects(response, "/")

    def test_other_file_extensions(self):
        form = DataSourceUploadForm(
            files={
                "episodes": SimpleUploadedFile("episodes.txt", b"episodes"),
                "header": SimpleUploadedFile("header.pdf", b"header"),
                "uasc": SimpleUploadedFile("uasc.xlsx", b"uasc"),
            }
        )

        self.assertFormError(form, "episodes", "File must have extension .csv")
        self.assertFormError(form, "header", "File must have extension .csv")
        self.assertFormError(form, "uasc", "File must have extension .csv")

    @patch("dm_regional_app.views.validate_with_prediction")
    def test_data_upload_success(self, prediction):
        files = {
            "episodes": SimpleUploadedFile("episodes.csv", b"episodes"),
            "header": SimpleUploadedFile("header.csv", b"header"),
            "uasc": SimpleUploadedFile("uasc.csv", b"uasc"),
        }

        # Mock the datacontainer created from the verifying the uploaded files
        datacontainer = MagicMock()
        type(datacontainer).data_start_date = datetime(2024, 1, 1)
        type(datacontainer).data_end_date = datetime(2024, 12, 1)
        prediction.return_value = datacontainer, None

        with mock.patch("django.core.files.storage.FileSystemStorage") as mock_storage:
            self.client.post(reverse("upload_data"), files)
            self.assertEqual(DataSource.objects.count(), 1)
            mock_storage.assert_called()

    @patch("dm_regional_app.views.validate_with_prediction")
    def test_data_upload_failure(self, prediction):
        files = {
            "episodes": SimpleUploadedFile("episodes.csv", b"episodes"),
            "header": SimpleUploadedFile("header.csv", b"header"),
            "uasc": SimpleUploadedFile("uasc.csv", b"uasc"),
        }
        prediction.return_value = None, None
        self.client.post(reverse("upload_data"), files)
        self.assertEqual(DataSource.objects.count(), 0)
