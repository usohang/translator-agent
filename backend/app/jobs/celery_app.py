from celery import Celery
from ..config import get_settings

cfg = get_settings()

celery_app = Celery(
    "translator",
    broker=cfg.redis_url,
    backend=cfg.redis_url,
)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Seoul",
    task_track_started=True,
    task_acks_late=True,
)
