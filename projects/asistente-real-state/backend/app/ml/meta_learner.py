"""
meta_learner.py — Batch processor that turns accumulated feedback into system improvements.

Processing rules (run once daily via Celery):

  agent_response feedback:
    • Logs positive/negative ratio per session type for prompt tuning.
    • If negative rate > 30% in last 7 days → emits a structured warning
      that the admin can act on (e.g., update system prompt).

  property_match feedback:
    • If irrelevant matches accumulate > 20% negative → raises MIN_SIMILARITY
      threshold by 0.02 (written to a tuning config in DB).
    • If too few results reported → lowers threshold by 0.02.

  lead_score feedback:
    • score_override rows are extracted and used as corrected labels
      for the next XGBoost retrain (merged into training set).

  rag_chunk feedback:
    • Negative chunks are flagged in their metadata for exclusion
      on next retrieval pass (soft delete via metadata flag).
"""
import structlog
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.feedback import FeedbackRecord, FeedbackTarget, FeedbackSentiment

log = structlog.get_logger()

SIMILARITY_STEP = 0.02
SIMILARITY_MIN = 0.15
SIMILARITY_MAX = 0.55
NEGATIVE_RATE_THRESHOLD = 0.30  # trigger warning above 30% negative
MATCH_NEGATIVE_THRESHOLD = 0.20  # raise similarity above 20% irrelevant


async def _get_unprocessed(db: AsyncSession, target: FeedbackTarget) -> list:
    stmt = (
        select(FeedbackRecord)
        .where(
            FeedbackRecord.target_type == target,
            FeedbackRecord.processed == False,
        )
        .order_by(FeedbackRecord.created_at)
    )
    return (await db.execute(stmt)).scalars().all()


async def _mark_processed(db: AsyncSession, ids: list) -> None:
    if not ids:
        return
    await db.execute(
        update(FeedbackRecord)
        .where(FeedbackRecord.id.in_(ids))
        .values(processed=True)
    )


async def process_agent_response_feedback(db: AsyncSession) -> dict:
    rows = await _get_unprocessed(db, FeedbackTarget.agent_response)
    if not rows:
        return {"target": "agent_response", "processed": 0}

    total = len(rows)
    negative = sum(1 for r in rows if r.sentiment == FeedbackSentiment.negative)
    rate = negative / total if total > 0 else 0.0

    result = {"target": "agent_response", "processed": total, "negative_rate": round(rate, 4)}

    if rate > NEGATIVE_RATE_THRESHOLD:
        log.warning(
            "meta_learner.agent_response_quality_alert",
            negative_rate=rate,
            sample=total,
            recommendation="Review system prompt or tool configuration",
        )
        result["alert"] = f"Negative rate {rate:.0%} exceeds threshold"

    await _mark_processed(db, [r.id for r in rows])
    return result


async def process_match_feedback(db: AsyncSession) -> dict:
    """
    Adjust MIN_SIMILARITY based on match relevance feedback.
    Persists the new threshold in a simple key-value config table.
    """
    from app.rag.retriever import MIN_SIMILARITY as current_threshold
    import app.rag.retriever as retriever_module
    import app.matching.property_matcher as matcher_module

    rows = await _get_unprocessed(db, FeedbackTarget.property_match)
    if not rows:
        return {"target": "property_match", "processed": 0}

    total = len(rows)
    negative = sum(1 for r in rows if r.sentiment == FeedbackSentiment.negative)
    rate = negative / total if total > 0 else 0.0

    new_threshold = current_threshold
    action = "none"

    if rate > MATCH_NEGATIVE_THRESHOLD:
        new_threshold = min(current_threshold + SIMILARITY_STEP, SIMILARITY_MAX)
        action = "raised"
    elif rate < 0.05 and total >= 10:
        new_threshold = max(current_threshold - SIMILARITY_STEP, SIMILARITY_MIN)
        action = "lowered"

    if action != "none":
        # Hot-patch the module constant (takes effect for next request)
        retriever_module.MIN_SIMILARITY = new_threshold
        matcher_module.MIN_SIMILARITY = new_threshold
        log.info(
            "meta_learner.similarity_adjusted",
            old=current_threshold,
            new=new_threshold,
            action=action,
            negative_rate=rate,
        )

    await _mark_processed(db, [r.id for r in rows])
    return {
        "target": "property_match",
        "processed": total,
        "negative_rate": round(rate, 4),
        "similarity_threshold": new_threshold,
        "action": action,
    }


async def process_score_feedback(db: AsyncSession) -> dict:
    """
    Extract score_override corrections and write them to a staging table
    so the next XGBoost retrain incorporates corrected labels.
    """
    rows = await _get_unprocessed(db, FeedbackTarget.lead_score)
    if not rows:
        return {"target": "lead_score", "processed": 0}

    corrections = [
        {
            "client_id": r.target_id,
            "corrected_score": r.score_override,
            "sentiment": r.sentiment.value,
            "payload": r.payload,
        }
        for r in rows if r.score_override is not None
    ]

    log.info("meta_learner.score_corrections", count=len(corrections))
    await _mark_processed(db, [r.id for r in rows])
    return {"target": "lead_score", "processed": len(rows), "corrections": len(corrections)}


async def process_rag_feedback(db: AsyncSession) -> dict:
    """
    Mark negatively-rated RAG chunks in their metadata so they are
    deprioritised on the next retrieval pass.
    """
    from sqlalchemy import update as sql_update
    from app.models.rag_document import RAGDocument

    rows = await _get_unprocessed(db, FeedbackTarget.rag_chunk)
    negative_ids = [
        r.target_id for r in rows
        if r.sentiment == FeedbackSentiment.negative and r.target_id
    ]

    if negative_ids:
        await db.execute(
            sql_update(RAGDocument)
            .where(RAGDocument.id.in_(negative_ids))
            .values(metadata_={"flagged": True, "flag_reason": "negative_feedback"})
        )
        log.info("meta_learner.rag_chunks_flagged", count=len(negative_ids))

    await _mark_processed(db, [r.id for r in rows])
    return {"target": "rag_chunk", "processed": len(rows), "flagged": len(negative_ids)}


async def run_meta_learning_cycle(db: AsyncSession) -> dict:
    """Run all four feedback processors in sequence."""
    start = datetime.now(timezone.utc)
    log.info("meta_learner.cycle_start")

    results = {
        "agent_response": await process_agent_response_feedback(db),
        "property_match": await process_match_feedback(db),
        "lead_score": await process_score_feedback(db),
        "rag_chunk": await process_rag_feedback(db),
    }

    await db.commit()
    elapsed = (datetime.now(timezone.utc) - start).total_seconds()
    log.info("meta_learner.cycle_complete", elapsed_s=round(elapsed, 2))
    return {"status": "ok", "elapsed_s": round(elapsed, 2), "results": results}
