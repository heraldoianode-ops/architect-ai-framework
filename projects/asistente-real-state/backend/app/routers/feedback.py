"""
feedback.py — Endpoints to submit and review system feedback.
Used by the dashboard (agents rate matches/scores) and the gateway
(auto-submits agent response sentiment from WhatsApp reactions).
"""
import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_agent_or_above, require_admin
from app.core.database import get_db
from app.models.feedback import FeedbackRecord, FeedbackTarget, FeedbackSentiment

router = APIRouter(prefix="/feedback", tags=["feedback"])


# ─── Schemas ──────────────────────────────────────────────────────────────────
class FeedbackIn(BaseModel):
    target_type: FeedbackTarget
    target_id: str | None = None
    sentiment: FeedbackSentiment
    score_override: float | None = Field(None, ge=0.0, le=1.0)
    payload: dict = Field(default_factory=dict)


class FeedbackOut(BaseModel):
    id: uuid.UUID
    target_type: FeedbackTarget
    target_id: str | None
    sentiment: FeedbackSentiment
    processed: bool
    model_config = {"from_attributes": True}


class MetaLearnResponse(BaseModel):
    status: str
    elapsed_s: float
    results: dict


# ─── Routes ────────────────────────────────────────────────────────────────────
@router.post("/", response_model=FeedbackOut, status_code=201)
async def submit_feedback(
    body: FeedbackIn,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_agent_or_above),
):
    """Submit a feedback event. Can be called by agents, the dashboard, or the gateway."""
    record = FeedbackRecord(
        target_type=body.target_type,
        target_id=body.target_id,
        agent_id=current_user.id,
        sentiment=body.sentiment,
        score_override=body.score_override,
        payload=body.payload,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


@router.get("/", response_model=list[FeedbackOut])
async def list_feedback(
    target_type: FeedbackTarget | None = Query(None),
    processed: bool | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _: Any = Depends(require_admin),
):
    stmt = select(FeedbackRecord).order_by(FeedbackRecord.created_at.desc()).limit(limit)
    if target_type:
        stmt = stmt.where(FeedbackRecord.target_type == target_type)
    if processed is not None:
        stmt = stmt.where(FeedbackRecord.processed == processed)
    return (await db.execute(stmt)).scalars().all()


@router.post("/run", response_model=MetaLearnResponse)
async def trigger_meta_learning(
    db: AsyncSession = Depends(get_db),
    _: Any = Depends(require_admin),
):
    """Manually trigger the meta-learning cycle (normally runs daily via Celery)."""
    from app.ml.meta_learner import run_meta_learning_cycle
    return await run_meta_learning_cycle(db)
