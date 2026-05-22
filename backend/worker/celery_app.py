from celery import Celery
from backend.config import settings

celery_app = Celery(
    "maskman_worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)

celery_app.conf.task_routes = {
    "backend.worker.tasks.*": {"queue": "default"}
}
