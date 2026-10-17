import os

from celery import Celery

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "config.settings",
)

app = Celery("opspilot")

app.config_from_object(
    "django.conf:settings",
    namespace="CELERY",
)

app.conf.update(
    broker_url=os.environ.get(
        "CELERY_BROKER_URL",
        "redis://127.0.0.1:6382/0",
    ),
    task_serializer="json",
    accept_content=["json"],
    task_ignore_result=True,
    broker_connection_retry_on_startup=True,
    task_default_queue="opspilot",
)

app.autodiscover_tasks()