import asyncio
import structlog
from sqlalchemy import select

from app.workers.celery_app import celery_app

log = structlog.get_logger()


@celery_app.task(name="app.workers.tasks.matching.embed_new_properties", bind=True)
def embed_new_properties(self):
    """
    Find all properties with embedding=NULL and generate their embeddings.
    Runs every 30 minutes via Celery beat to keep the index fresh after scraping.
    """
    from app.core.database import SyncSessionLocal
    from app.models.property import Property

    with SyncSessionLocal() as db:
        ids = db.execute(
            select(Property.id).where(Property.embedding.is_(None)).limit(200)
        ).scalars().all()

    if not ids:
        log.info("embed_new_properties.nothing_to_do")
        return {"embedded": 0}

    log.info("embed_new_properties.start", count=len(ids))

    async def _run():
        from app.core.database import AsyncSessionLocal
        from app.matching.preference_embedder import embed_property
        ok = 0
        async with AsyncSessionLocal() as db:
            for pid in ids:
                try:
                    if await embed_property(str(pid), db):
                        ok += 1
                except Exception as exc:
                    log.warning("embed_property.error", id=str(pid), error=str(exc))
        return ok

    embedded = asyncio.run(_run())
    log.info("embed_new_properties.done", embedded=embedded)
    return {"embedded": embedded}
