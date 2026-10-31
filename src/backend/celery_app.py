"""Celery Application Setup for Asynchronous Background Processing."""

from celery import Celery
from ..config import settings

celery_app = Celery(
    "traffic_tasks",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Ho_Chi_Minh",
    enable_utc=True,
    task_track_started=True,
)
