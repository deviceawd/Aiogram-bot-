# celery_app.py
from celery import Celery

celery_app = Celery(
    "tasks",
    broker="redis://host.docker.internal:6379/0",     # Redis как брокер
    backend=None,                          # result_backend не нужен
    include=["tasks"],                     # где лежат таски
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_expires=3600,
    timezone="UTC",
)