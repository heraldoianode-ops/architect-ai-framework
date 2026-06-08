import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_user, require_agent_or_above
from app.models.user import User, UserRole
from app.models.event import Event, EventStatus
from app.schemas.event import EventCreate, EventUpdate, EventRead

router = APIRouter(prefix="/events", tags=["events"])


@router.get("", response_model=list[EventRead])
async def list_events(
    from_date: datetime | None = Query(None),
    to_date: datetime | None = Query(None),
    event_status: str | None = Query(None),
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_agent_or_above),
):
    stmt = select(Event)
    filters = []

    if current_user.role == UserRole.agente_real_state:
        filters.append(Event.agent_id == current_user.id)
    if from_date:
        filters.append(Event.scheduled_at >= from_date)
    if to_date:
        filters.append(Event.scheduled_at <= to_date)
    if event_status:
        filters.append(Event.status == event_status)

    if filters:
        stmt = stmt.where(and_(*filters))

    stmt = stmt.order_by(Event.scheduled_at.asc()).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("", response_model=EventRead, status_code=status.HTTP_201_CREATED)
async def create_event(
    body: EventCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_agent_or_above),
):
    event = Event(**body.model_dump(), agent_id=current_user.id)
    db.add(event)
    await db.flush()
    return event


@router.patch("/{event_id}", response_model=EventRead)
async def update_event(
    event_id: uuid.UUID,
    body: EventUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_agent_or_above),
):
    result = await db.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Evento no encontrado")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(event, field, value)
    return event


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_event(
    event_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_agent_or_above),
):
    result = await db.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Evento no encontrado")
    event.status = EventStatus.cancelado
