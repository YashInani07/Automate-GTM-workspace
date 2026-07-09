from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

celery_app = Celery(
    "gtm_workflow",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.worker.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    beat_schedule={
        "poll-inbox-for-replies": {
            "task": "app.worker.tasks.poll_inbox_for_replies",
            "schedule": crontab(minute=f"*/{max(1, settings.REPLY_POLL_INTERVAL_MINUTES)}"),
        },
        "sweep-overdue-messages": {
            "task": "app.worker.tasks.sweep_overdue_messages",
            "schedule": crontab(minute="*/10"),
        },
    },
)
