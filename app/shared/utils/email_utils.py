"""Email sending utilities via Mailtrap SMTP.

Handles alert email delivery using Mailtrap for development/testing and console output for dev mode.
"""

import os
from jinja2 import Template
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def generate_unsubscribe_link(user_email: str) -> str:
    """Generate an unsubscribe link for the user.

    Args:
        user_email: User's email address

    Returns:
        str: Unsubscribe URL with email as query parameter
    """
    base_url = os.getenv("APP_BASE_URL", "https://app.aeterna.ai")
    return f"{base_url}/unsubscribe?email={user_email}"


def send_password_reset_email(to_email: str, reset_token: str) -> bool:
    """Send a password reset email to a user.

    Args:
        to_email: Recipient email address
        reset_token: Password reset token for email verification

    Returns:
        bool: True if email sent successfully or logged, False on error
    """
    base_url = os.getenv("APP_BASE_URL", "https://app.aeterna.ai")
    reset_link = f"{base_url}/reset-password?token={reset_token}"

    subject = "Password Reset Request - AETERNA"
    html_content = f"""
    <h2>Password Reset Request</h2>
    <p>You requested a password reset for your AETERNA account.</p>
    <p>Click the link below to reset your password (valid for 24 hours):</p>
    <p><a href="{reset_link}">Reset Password</a></p>
    <p>If you didn't request this, please ignore this email.</p>
    """

    return send_email_alert(to_email, subject, html_content, reset_link)


def send_email_alert(
    to_email: str, subject: str, html_content: str, link: str = None
) -> bool:
    """Send an alert email to a user.

    Uses Mailtrap SMTP if credentials are configured, otherwise logs to console in dev mode.

    Args:
        to_email: Recipient email address
        subject: Email subject line
        html_content: HTML content for email body
        link: Optional link to include in email

    Returns:
        bool: True if email sent successfully or logged, False on error
    """
    SENDER_EMAIL = os.getenv("SENDER_EMAIL", "noreply@example.com")

    # Mailtrap credentials
    MAILTRAP_HOST = os.getenv("MAILTRAP_HOST", "sandbox.smtp.mailtrap.io")
    MAILTRAP_PORT = int(os.getenv("MAILTRAP_PORT", 2525))
    MAILTRAP_USERNAME = os.getenv("MAILTRAP_USERNAME")
    MAILTRAP_PASSWORD = os.getenv("MAILTRAP_PASSWORD")

    # Render HTML template
    template_path = os.path.join(os.path.dirname(__file__), "email_template.html")
    with open(template_path, "r", encoding="utf-8") as f:
        template = Template(f.read())

    unsubscribe_link = generate_unsubscribe_link(to_email)
    rendered_html = template.render(
        title=subject, body=html_content, link=link, unsubscribe_link=unsubscribe_link
    )

    if MAILTRAP_USERNAME and MAILTRAP_PASSWORD:
        # Use Mailtrap SMTP for development/testing
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = SENDER_EMAIL
            msg["To"] = to_email
            msg.attach(MIMEText(rendered_html, "html"))

            with smtplib.SMTP(MAILTRAP_HOST, MAILTRAP_PORT) as server:
                server.starttls()
                server.login(MAILTRAP_USERNAME, MAILTRAP_PASSWORD)
                server.sendmail(SENDER_EMAIL, to_email, msg.as_string())
            print(f"[EMAIL-MAILTRAP] Sent to {to_email} via Mailtrap SMTP.")
            return True
        except Exception as e:
            print(f"[EMAIL-ERROR][Mailtrap] Exception sending to {to_email}: {e}")
            return False
    else:
        # Dev mode: print to console
        print(
            f"[EMAIL-DEV] To: {to_email} | Subject: {subject}\nContent: {rendered_html[:100]}..."
        )
        return True
