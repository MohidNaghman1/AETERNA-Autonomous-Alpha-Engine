import os
import pytest
from app.shared.utils.email_utils import send_email_alert

def test_send_email_alert():
    to_email = "test@example.com"
    subject = "Mailtrap Test Email"
    html_content = "<h1>Mailtrap Test</h1><p>This is a test email sent via Mailtrap SMTP.</p>"
    link = "https://aeterna.ai"

    result = send_email_alert(to_email, subject, html_content, link)
    assert result is True
    # Check Mailtrap inbox for the email

if __name__ == "__main__":
    pytest.main([__file__])
