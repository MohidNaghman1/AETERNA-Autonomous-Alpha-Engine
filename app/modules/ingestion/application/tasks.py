from .celery_app import celery_app
from app.modules.ingestion.application.rss_collector import run_collector as run_rss
from app.modules.ingestion.application.price_collector import run_collector as run_price
from app.modules.ingestion.application.onchain_collector import (
    run_collector as run_onchain,
)


@celery_app.task(name="app.modules.ingestion.application.tasks.run_rss_collector")
def run_rss_collector():
    run_rss()


@celery_app.task(name="app.modules.ingestion.application.tasks.run_price_collector")
def run_price_collector():
    run_price()


@celery_app.task(name="app.modules.ingestion.application.tasks.run_onchain_collector")
def run_onchain_collector():
    run_onchain()
