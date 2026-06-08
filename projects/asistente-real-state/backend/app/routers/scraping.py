"""
scraping.py — Admin endpoints to manage scraping sources and trigger manual runs.
All endpoints require administrador role.
"""
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_admin
from app.core.database import get_db
from app.models.scraping_source import ScrapingSource, SourceType

router = APIRouter(prefix="/admin/scraping", tags=["scraping"])


# ─── Schemas ──────────────────────────────────────────────────────────────────
class ScrapingSourceCreate(BaseModel):
    name: str = Field(..., max_length=120)
    source_type: SourceType
    is_active: bool = True
    config: dict[str, Any] = Field(default_factory=dict)


class ScrapingSourceUpdate(BaseModel):
    name: str | None = None
    is_active: bool | None = None
    config: dict[str, Any] | None = None


class ScrapingSourceOut(BaseModel):
    id: uuid.UUID
    name: str
    source_type: SourceType
    is_active: bool
    last_run_at: datetime | None
    last_run_status: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Routes ───────────────────────────────────────────────────────────────────
@router.get("/sources", response_model=list[ScrapingSourceOut])
async def list_sources(
    db: AsyncSession = Depends(get_db),
    _: Any = Depends(require_admin),
):
    result = await db.execute(select(ScrapingSource).order_by(ScrapingSource.created_at.desc()))
    return result.scalars().all()


@router.post("/sources", response_model=ScrapingSourceOut, status_code=status.HTTP_201_CREATED)
async def create_source(
    body: ScrapingSourceCreate,
    db: AsyncSession = Depends(get_db),
    _: Any = Depends(require_admin),
):
    source = ScrapingSource(**body.model_dump())
    db.add(source)
    await db.commit()
    await db.refresh(source)
    return source


@router.patch("/sources/{source_id}", response_model=ScrapingSourceOut)
async def update_source(
    source_id: uuid.UUID,
    body: ScrapingSourceUpdate,
    db: AsyncSession = Depends(get_db),
    _: Any = Depends(require_admin),
):
    result = await db.execute(select(ScrapingSource).where(ScrapingSource.id == source_id))
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(source, field, value)

    await db.commit()
    await db.refresh(source)
    return source


@router.delete("/sources/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_source(
    source_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: Any = Depends(require_admin),
):
    result = await db.execute(select(ScrapingSource).where(ScrapingSource.id == source_id))
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    await db.delete(source)
    await db.commit()


@router.post("/sources/{source_id}/run", status_code=status.HTTP_202_ACCEPTED)
async def trigger_manual_run(
    source_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: Any = Depends(require_admin),
):
    """Enqueue an immediate scraping run for the given source."""
    result = await db.execute(select(ScrapingSource).where(ScrapingSource.id == source_id))
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    if not source.is_active:
        raise HTTPException(status_code=400, detail="Source is disabled")

    from app.workers.tasks.scraping import run_adinco_scraper
    run_adinco_scraper.apply_async()

    source.last_run_at = datetime.now(timezone.utc)
    source.last_run_status = "queued"
    await db.commit()

    return {"queued": True, "source_id": str(source_id)}


@router.post("/circuit-breaker/{source_id}/reset", status_code=status.HTTP_200_OK)
async def reset_circuit_breaker(
    source_id: str,
    _: Any = Depends(require_admin),
):
    """Manually reset an open circuit breaker for a scraping source."""
    from app.scraping.adinco_scraper import circuit_breaker
    circuit_breaker.reset(source_id)
    return {"reset": True, "source_id": source_id}
