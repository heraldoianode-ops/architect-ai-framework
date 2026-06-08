from app.workers.celery_app import celery_app
import structlog

log = structlog.get_logger()


@celery_app.task(name="app.workers.tasks.reminders.send_upcoming_reminders")
def send_upcoming_reminders():
    """Send WhatsApp + email reminders for events in the next 24h / 1h. Nodo 6.2."""
    log.info("reminders.check_start")
    # TODO: Nodo 6.2 — query events, check reminder windows, call gateway + Resend
    log.info("reminders.check_complete")
