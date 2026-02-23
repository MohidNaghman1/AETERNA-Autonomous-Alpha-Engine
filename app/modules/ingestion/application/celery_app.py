from celery import Celery
import os

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

celery_app = Celery(
    "ingestion_tasks",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND
)

celery_app.conf.beat_schedule = {
    "run_rss_collector": {
        "task": "app.modules.ingestion.application.tasks.run_rss_collector",
        "schedule": 60.0,
    },
    "run_price_collector": {
        "task": "app.modules.ingestion.application.tasks.run_price_collector",
        "schedule": 60.0,
    },
}

celery_app.conf.timezone = "UTC"
