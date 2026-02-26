from dotenv import load_dotenv
load_dotenv()

from app.shared.utils.email_utils import send_email_alert

send_email_alert(
    to_email="mohidnaghman0@gmail.com",
    subject="Test Email from Resend",
    html_content="<h1>Hello from AETERNA!</h1><p>This is a test email.</p>"
)