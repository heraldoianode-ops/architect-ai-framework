import asyncio
import structlog

from app.workers.celery_app import celery_app

log = structlog.get_logger()


@celery_app.task(name="app.workers.tasks.meta_learning.run_meta_learning_cycle")
def run_meta_learning_cycle():
    """Daily task: process accumulated feedback to improve matching, scoring, and RAG."""
    async def _run():
        from app.core.database import AsyncSessionLocal
        from app.ml.meta_learner import run_meta_learning_cycle as _cycle
        async with AsyncSessionLocal() as db:
            return await _cycle(db)

    result = asyncio.run(_run())
    log.info("meta_learning_cycle.done", **{k: v for k, v in result.items() if k != "results"})
    return result
