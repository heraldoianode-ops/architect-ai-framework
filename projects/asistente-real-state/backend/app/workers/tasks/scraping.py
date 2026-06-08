import asyncio
import structlog
from sqlalchemy import select

from app.workers.celery_app import celery_app

log = structlog.get_logger()


@celery_app.task(name="app.workers.tasks.scraping.run_adinco_scraper", bind=True, max_retries=3)
def run_adinco_scraper(self):
    """RPA task: scrape all active Adinco sources. Runs every 6h via beat."""
    from app.core.database import SyncSessionLocal
    from app.models.scraping_source import ScrapingSource
    from app.scraping.adinco_scraper import run_scraper

    with SyncSessionLocal() as db:
        sources = db.execute(
            select(ScrapingSource).where(
                ScrapingSource.source_type == "adinco",
                ScrapingSource.is_active == True,
            )
        ).scalars().all()

    if not sources:
        log.info("adinco_scraper.no_active_sources")
        return

    results = []
    for source in sources:
        config = {**source.config, "id": str(source.id)}
        try:
            result = asyncio.run(run_scraper(config))
            results.append(result)
            log.info("adinco_scraper.source_done", source_id=str(source.id), status=result.get("status"))
        except Exception as exc:
            log.error("adinco_scraper.source_error", source_id=str(source.id), error=str(exc))
            raise self.retry(exc=exc, countdown=300)

    return results


@celery_app.task(name="app.workers.tasks.scraping.sync_google_drive", bind=True, max_retries=3)
def sync_google_drive(self):
    """Sync all active Google Drive sources → properties/contacts. Runs every 12h via beat."""
    from app.core.database import SyncSessionLocal
    from app.models.scraping_source import ScrapingSource
    from app.scraping.drive_scraper import run_drive_sync

    with SyncSessionLocal() as db:
        sources = db.execute(
            select(ScrapingSource).where(
                ScrapingSource.source_type == "google_drive",
                ScrapingSource.is_active == True,
            )
        ).scalars().all()

    if not sources:
        log.info("drive_sync.no_active_sources")
        return

    results = []
    for source in sources:
        config = {**source.config, "id": str(source.id)}
        try:
            result = asyncio.run(run_drive_sync(config))
            results.append(result)
            log.info("drive_sync.source_done", source_id=str(source.id), status=result.get("status"))
        except Exception as exc:
            log.error("drive_sync.source_error", source_id=str(source.id), error=str(exc))
            raise self.retry(exc=exc, countdown=600)

    return results
