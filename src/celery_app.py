"""Celery application configuration."""

from celery import Celery

from src.config import get_settings

settings = get_settings()
broker = settings.celery_broker_url or settings.redis_url
backend = settings.celery_result_backend or settings.redis_url

celery_app = Celery("acquirec", broker=broker, backend=backend)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,
    worker_prefetch_multiplier=1,
)
