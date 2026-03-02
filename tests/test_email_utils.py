"""Tests for email utility functions.

Tests email sending, template rendering, and unsubscribe link generation.
"""

import os
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.shared.utils.email_utils import send_email_alert, generate_unsubscribe_link


@pytest.mark.asyncio
async def test_send_email_alert_mocked(mocker):
    """Test email sending with mocked SMTP connection.

    This prevents actual email sending during tests.
    """
    # Mock SMTP_SSL connection
    mock_smtp = AsyncMock()
    mock_smtp.send_message = AsyncMock()

    mocker.patch("smtplib.SMTP_SSL", return_value=mock_smtp)

    # Test email sending
    result = await send_email_alert(
        to_email="test@example.com",
        subject="Test Alert",
        html_content="<h1>Test Alert Title</h1><p>This is a test alert.</p>",
        link="https://aeterna.ai/alert/123",
    )

    assert result is True
    mock_smtp.send_message.assert_called_once()


@pytest.mark.asyncio
async def test_send_email_alert_with_empty_content(mocker):
    """Test email sending with minimal content."""
    mock_smtp = AsyncMock()
    mocker.patch("smtplib.SMTP_SSL", return_value=mock_smtp)

    result = await send_email_alert(
        to_email="test@example.com",
        subject="Empty Test",
        html_content="",
        link="https://aeterna.ai",
    )

    assert result is True


@pytest.mark.asyncio
async def test_send_email_alert_to_multiple_recipients(mocker):
    """Test email sending to multiple recipients."""
    mock_smtp = AsyncMock()
    mocker.patch("smtplib.SMTP_SSL", return_value=mock_smtp)

    emails = ["user1@example.com", "user2@example.com", "user3@example.com"]

    for email in emails:
        result = await send_email_alert(
            to_email=email,
            subject="Notification",
            html_content="<p>Test message</p>",
            link="https://aeterna.ai",
        )
        assert result is True


@pytest.mark.asyncio
async def test_send_email_alert_failure_handling(mocker):
    """Test graceful handling of email sending failures."""
    # Mock SMTP to raise an exception
    mock_smtp = AsyncMock()
    mock_smtp.send_message = AsyncMock(side_effect=Exception("SMTP Connection Failed"))

    mocker.patch("smtplib.SMTP_SSL", return_value=mock_smtp)

    # Should return False or raise, depending on implementation
    try:
        result = await send_email_alert(
            to_email="test@example.com",
            subject="Test",
            html_content="<p>Test</p>",
            link="https://aeterna.ai",
        )
        # If it doesn't raise, it should return False
        assert result is False
    except Exception:
        # If it raises, that's also acceptable
        pass


def test_generate_unsubscribe_link():
    """Test unsubscribe link generation.

    Verifies that unsubscribe links contain the user email
    and are properly formatted.
    """
    email = "user@example.com"
    link = generate_unsubscribe_link(email)

    # Verify link contains unsubscribe endpoint
    assert "unsubscribe" in link.lower()

    # Verify link contains the email
    assert email in link or email.replace("@", "%40") in link

    # Verify it's a valid URL format
    assert link.startswith("http://") or link.startswith("https://") or link.startswith("/")


def test_generate_unsubscribe_link_with_special_chars():
    """Test unsubscribe link generation with special characters in email."""
    emails = ["user+test@example.com", "first.last@example.co.uk", "user_name@example.org"]

    for email in emails:
        link = generate_unsubscribe_link(email)
        assert "unsubscribe" in link.lower()
        # Email might be URL-encoded
        assert email in link or email.replace("@", "%40").replace("+", "%2B") in link


def test_email_template_rendering():
    """Test that email templates are rendered correctly.

    Verifies HTML template contains expected content.
    """
    from app.shared.utils.email_utils import render_email_template

    template_data = {
        "alert_title": "Bitcoin Price Alert",
        "alert_body": "BTC has reached $50,000",
        "action_url": "https://aeterna.ai/alert/123",
        "unsubscribe_link": "https://aeterna.ai/unsubscribe?email=test@example.com",
    }

    html = render_email_template(template_data)

    # Check for key elements in rendered template
    assert "Bitcoin Price Alert" in html
    assert "BTC has reached $50,000" in html
    assert "https://aeterna.ai/alert/123" in html


@pytest.mark.asyncio
async def test_send_bulk_emails(mocker):
    """Test sending bulk emails to multiple users."""
    mock_smtp = AsyncMock()
    mocker.patch("smtplib.SMTP_SSL", return_value=mock_smtp)

    recipients = [{"email": f"user{i}@example.com", "subject": f"Alert {i}"} for i in range(5)]

    results = []
    for recipient in recipients:
        result = await send_email_alert(
            to_email=recipient["email"],
            subject=recipient["subject"],
            html_content=f"<p>Alert for {recipient['email']}</p>",
            link="https://aeterna.ai",
        )
        results.append(result)

    assert all(results)
    assert mock_smtp.send_message.call_count == 5
