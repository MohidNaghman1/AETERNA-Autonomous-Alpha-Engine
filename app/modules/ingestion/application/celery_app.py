from celery import Celery
import os
from celery.schedules import crontab

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

celery_app = Celery(
    "ingestion_tasks", broker=CELERY_BROKER_URL, backend=CELERY_RESULT_BACKEND
)

# Example beat schedule
celery_app.conf.beat_schedule = {
    "run-rss-collector": {
        "task": "app.modules.ingestion.application.tasks.run_rss_collector",
        "schedule": crontab(minute="*/1"),  # Every minute
    },
    "run-price-collector": {
        "task": "app.modules.ingestion.application.tasks.run_price_collector",
        "schedule": crontab(minute="*/1"),  # Every minute
    },
    "run-onchain-collector": {
        "task": "app.modules.ingestion.application.tasks.run_onchain_collector",
        "schedule": crontab(minute="*/1"),  # Every minute (or adjust as needed)
    },
}

celery_app.conf.timezone = "UTC"
