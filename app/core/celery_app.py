"""Celery application and queue configuration (Task 16)."""

import os
from celery import Celery
from app.core.config import get_settings

settings = get_settings()
broker_url = settings.celery_broker_url or os.getenv("CELERY_BROKER_URL") or settings.redis_url
result_backend = settings.celery_result_backend or os.getenv("CELERY_RESULT_BACKEND") or settings.redis_url

celery_app = Celery(
    "ledgerforge_worker",
    broker=broker_url,
    backend=result_backend,
    include=["app.worker"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    broker_connection_retry_on_startup=True,
    task_time_limit=1800,  # 30 min limit for long batch runs
)
