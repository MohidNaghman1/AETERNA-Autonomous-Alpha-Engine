from celery import Celery
from datetime import datetime, timedelta
from app.shared.utils.email_utils import send_email_alert
import os
import json

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

celery_app = Celery(
    "digest_tasks",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND
)

# In production, use persistent storage (DB)
USER_DIGESTS = {}  # user_id/email -> list of alerts

def add_alert_to_digest(user_email, alert):
    if user_email not in USER_DIGESTS:
        USER_DIGESTS[user_email] = []
    USER_DIGESTS[user_email].append(alert)

@celery_app.task(name="send_daily_digests")
def send_daily_digests():
    for user_email, alerts in USER_DIGESTS.items():
        if not alerts:
            continue
        html_content = "<h2>Your Daily Digest</h2>"
        for alert in alerts:
            html_content += f"<div><b>{alert['title']}</b><br>{alert['body']}</div><hr>"
        send_email_alert(
            to_email=user_email,
            subject="Your Daily Digest from AETERNA",
            html_content=html_content
        )
        USER_DIGESTS[user_email] = []  # Clear after sending

# To use: call add_alert_to_digest(email, alert) when email_frequency == 'daily_digest'
# Schedule send_daily_digests to run daily via celery beat
