import json

import requests
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend
from django.core.mail.message import sanitize_address


class SendGridEmailBackend(BaseEmailBackend):
    """
    Custom Django email backend using SendGrid's REST API
    instead of the vulnerable sendgrid-python SDK (https://security.snyk.io/vuln/SNYK-PYTHON-ECDSA-6184115).
    """

    sendgrid_api_url = "https://api.sendgrid.com/v3/mail/send"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.api_key = getattr(settings, "SENDGRID_API_KEY", None)
        if not self.api_key:
            raise ValueError("SENDGRID_API_KEY must be set in Django settings.")

    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        sent_count = 0
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        for message in email_messages:
            try:
                from_email = sanitize_address(message.from_email, message.encoding)
                personalizations = [
                    {
                        "to": [
                            {"email": sanitize_address(addr, message.encoding)}
                            for addr in message.to
                        ],
                        "subject": message.subject,
                    }
                ]

                content = []
                if message.body:
                    content.append({"type": "text/plain", "value": message.body})

                # Handle alternative (HTML) attachments if provided
                for alt in message.alternatives:
                    mimetype, body = alt
                    content.append({"type": mimetype, "value": body})

                data = {
                    "personalizations": personalizations,
                    "from": {"email": from_email},
                    "content": content,
                }

                response = requests.post(
                    self.sendgrid_api_url,
                    headers=headers,
                    data=json.dumps(data),
                    timeout=10,
                )

                if 200 <= response.status_code < 300:
                    sent_count += 1
                else:
                    if not self.fail_silently:
                        raise Exception(
                            f"SendGrid API error {response.status_code}: {response.text}"
                        )

            except Exception:
                if not self.fail_silently:
                    raise

        return sent_count
