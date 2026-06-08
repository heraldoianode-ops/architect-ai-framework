from app.workers.celery_app import celery_app
import structlog

log = structlog.get_logger()


@celery_app.task(name="app.workers.tasks.scraping.run_adinco_scraper", bind=True, max_retries=3)
def run_adinco_scraper(self):
    """RPA task: scrape Adinco CRM for new properties/contacts. Nodo 3.1."""
    log.info("adinco_scraper.start")
    # TODO: Nodo 3.1 — Playwright headless login + HTML extraction
    log.info("adinco_scraper.complete")


@celery_app.task(name="app.workers.tasks.scraping.sync_google_drive")
def sync_google_drive():
    """Sync configured Google Drive folders to local DB. Nodo 3.2."""
    log.info("drive_sync.start")
    # TODO: Nodo 3.2 — Google Drive API + OpenPyXL ingestion
    log.info("drive_sync.complete")
