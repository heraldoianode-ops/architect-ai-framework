import asyncio
import structlog

from app.workers.celery_app import celery_app

log = structlog.get_logger()


@celery_app.task(name="app.workers.tasks.ml.retrain_lead_scorer")
def retrain_lead_scorer():
    """
    Weekly scheduled task: retrain XGBoost lead scoring model from current DB.
    Skipped automatically if fewer than MIN_TRAINING_SAMPLES labeled clients exist.
    """
    async def _run():
        from app.core.database import AsyncSessionLocal
        from app.ml.trainer import run_training_pipeline
        async with AsyncSessionLocal() as db:
            return await run_training_pipeline(db)

    result = asyncio.run(_run())
    log.info("retrain_lead_scorer.done", **result)
    return result
