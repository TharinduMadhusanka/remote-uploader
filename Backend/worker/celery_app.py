from celery import Celery
from shared.config import get_settings

settings = get_settings()

app = Celery(
    "transloader",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["worker.tasks.download"]
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    worker_concurrency=settings.celery_worker_concurrency,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)
