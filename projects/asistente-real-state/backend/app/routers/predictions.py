"""
predictions.py — Lead scoring endpoints.

GET  /predictions/clients/{id}        — score a single client
POST /predictions/clients/batch       — score multiple clients
POST /predictions/train               — trigger model retraining (admin only)
"""
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_admin, require_agent_or_above
from app.core.database import get_db
from app.models.client import Client
from app.models.interaction import Interaction
from app.models.event import Event
from app.ml.features import extract_features
from app.ml.predictor import score_lead

router = APIRouter(prefix="/predictions", tags=["predictions"])


# ─── Schemas ──────────────────────────────────────────────────────────────────
class ScoreOut(BaseModel):
    client_id: str
    score: float
    label: str
    model_used: str
    top_features: list[tuple[str, float]]


class BatchScoreIn(BaseModel):
    client_ids: list[uuid.UUID] = Field(..., min_length=1, max_length=100)


class TrainResponse(BaseModel):
    status: str
    samples: int | None = None
    positive: int | None = None
    negative: int | None = None
    reason: str | None = None


# ─── Helpers ──────────────────────────────────────────────────────────────────
async def _score_client(client_id: uuid.UUID, db: AsyncSession) -> ScoreOut:
    result = await db.execute(select(Client).where(Client.id == client_id))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail=f"Client {client_id} not found")

    interactions = (
        await db.execute(select(Interaction).where(Interaction.client_id == client_id))
    ).scalars().all()

    events = (
        await db.execute(select(Event).where(Event.client_id == client_id))
    ).scalars().all()

    features = extract_features(client, interactions, events)
    result_score = score_lead(features)

    return ScoreOut(
        client_id=str(client_id),
        score=result_score.score,
        label=result_score.label,
        model_used=result_score.model_used,
        top_features=result_score.top_features,
    )


# ─── Routes ────────────────────────────────────────────────────────────────────
@router.get("/clients/{client_id}", response_model=ScoreOut)
async def score_client(
    client_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: Any = Depends(require_agent_or_above),
):
    """Return the closing probability score for a single client."""
    return await _score_client(client_id, db)


@router.post("/clients/batch", response_model=list[ScoreOut])
async def score_batch(
    body: BatchScoreIn,
    db: AsyncSession = Depends(get_db),
    _: Any = Depends(require_agent_or_above),
):
    """Score multiple clients in one request (used by the Kanban board dashboard)."""
    results = []
    for cid in body.client_ids:
        try:
            results.append(await _score_client(cid, db))
        except HTTPException:
            pass  # skip missing clients silently in batch mode
    return results


@router.post("/train", response_model=TrainResponse)
async def trigger_training(
    db: AsyncSession = Depends(get_db),
    _: Any = Depends(require_admin),
):
    """Trigger an immediate model retraining from current DB data."""
    from app.ml.trainer import run_training_pipeline
    result = await run_training_pipeline(db)
    return result
