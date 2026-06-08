from celery import Celery
from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "ars_workers",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.workers.tasks.scraping",
        "app.workers.tasks.analytics",
        "app.workers.tasks.reminders",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="America/Argentina/Buenos_Aires",
    enable_utc=True,
    beat_schedule={
        "scraping-adinco-every-6h": {
            "task": "app.workers.tasks.scraping.run_adinco_scraper",
            "schedule": 21600,  # 6 hours
        },
        "sync-drive-every-12h": {
            "task": "app.workers.tasks.scraping.sync_google_drive",
            "schedule": 43200,  # 12 hours
        },
        "send-event-reminders-every-15min": {
            "task": "app.workers.tasks.reminders.send_upcoming_reminders",
            "schedule": 900,  # 15 minutes
        },
    },
)
