"""
crm.py — CRM endpoints: Kanban board, full-text search, interaction log, lead stage transitions.
Agents see only their own clients; brokers/admins see all.
"""
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select, or_, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.auth import get_current_user, require_agent_or_above
from app.core.database import get_db
from app.models.client import Client, LeadStage, LEAD_STAGE_ORDER
from app.models.interaction import Interaction, InteractionType
from app.models.user import User, UserRole

router = APIRouter(prefix="/crm", tags=["crm"])


# ─── Schemas ──────────────────────────────────────────────────────────────────
class ClientCard(BaseModel):
    id: uuid.UUID
    full_name: str
    email: str | None
    phone: str | None
    source: str | None
    lead_stage: LeadStage
    created_at: datetime
    model_config = {"from_attributes": True}


class KanbanColumn(BaseModel):
    stage: LeadStage
    count: int
    clients: list[ClientCard]


class StageTransitionIn(BaseModel):
    stage: LeadStage


class InteractionIn(BaseModel):
    interaction_type: InteractionType
    content: str = Field(..., min_length=1, max_length=4000)


class InteractionOut(BaseModel):
    id: uuid.UUID
    interaction_type: InteractionType
    content: str
    agent_id: uuid.UUID | None
    created_at: datetime
    model_config = {"from_attributes": True}


class ClientSummary(BaseModel):
    client: ClientCard
    recent_interactions: list[InteractionOut]
    total_interactions: int


# ─── Helpers ──────────────────────────────────────────────────────────────────
def _scope_query(q, current_user: User):
    """Filter clients to agent's own unless broker/admin."""
    if current_user.role in (UserRole.administrador, UserRole.broker):
        return q
    return q.where(Client.agent_id == current_user.id)


async def _get_client_or_404(client_id: uuid.UUID, db: AsyncSession, current_user: User) -> Client:
    stmt = _scope_query(select(Client).where(Client.id == client_id), current_user)
    result = await db.execute(stmt)
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


# ─── Kanban board ─────────────────────────────────────────────────────────────
@router.get("/kanban", response_model=list[KanbanColumn])
async def get_kanban(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_agent_or_above),
):
    """Return all lead stages as Kanban columns with their clients (max 50 per column)."""
    columns: list[KanbanColumn] = []

    for stage in LeadStage:
        stmt = _scope_query(
            select(Client).where(Client.lead_stage == stage).order_by(Client.updated_at.desc()).limit(50),
            current_user,
        )
        result = await db.execute(stmt)
        clients = result.scalars().all()

        count_stmt = _scope_query(
            select(func.count()).select_from(Client).where(Client.lead_stage == stage),
            current_user,
        )
        total = (await db.execute(count_stmt)).scalar_one()

        columns.append(KanbanColumn(stage=stage, count=total, clients=clients))

    return columns


# ─── Full-text search ──────────────────────────────────────────────────────────
@router.get("/search", response_model=list[ClientCard])
async def search_clients(
    q: str = Query(..., min_length=2, max_length=200),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_agent_or_above),
):
    """
    Full-text search over client name, email, phone, and notes.
    Falls back to ILIKE prefix search if FTS returns nothing.
    """
    # PostgreSQL plainto_tsquery for natural-language input
    tsquery = func.plainto_tsquery("spanish", q)
    tsvector = func.to_tsvector(
        "spanish",
        func.coalesce(Client.full_name, "") + " " +
        func.coalesce(Client.email, "") + " " +
        func.coalesce(Client.notes, ""),
    )

    stmt = _scope_query(
        select(Client)
        .where(tsvector.op("@@")(tsquery))
        .order_by(func.ts_rank(tsvector, tsquery).desc())
        .limit(limit),
        current_user,
    )
    result = await db.execute(stmt)
    clients = result.scalars().all()

    # Fallback: ILIKE on name/email/phone
    if not clients:
        pattern = f"%{q}%"
        fallback_stmt = _scope_query(
            select(Client).where(
                or_(
                    Client.full_name.ilike(pattern),
                    Client.email.ilike(pattern),
                    Client.phone.ilike(pattern),
                )
            ).limit(limit),
            current_user,
        )
        result = await db.execute(fallback_stmt)
        clients = result.scalars().all()

    return clients


# ─── Stage transitions ──────────────────────────────────────────────────────────
@router.patch("/clients/{client_id}/stage", response_model=ClientCard)
async def update_stage(
    client_id: uuid.UUID,
    body: StageTransitionIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_agent_or_above),
):
    """Move a client to a new Kanban stage and log the transition as an interaction."""
    client = await _get_client_or_404(client_id, db, current_user)
    old_stage = client.lead_stage

    if old_stage == body.stage:
        return client

    client.lead_stage = body.stage
    client.updated_at = datetime.now(timezone.utc)

    interaction = Interaction(
        client_id=client.id,
        agent_id=current_user.id,
        interaction_type=InteractionType.note,
        content=f"Etapa cambiada: {old_stage.value} → {body.stage.value}",
    )
    db.add(interaction)
    await db.commit()
    await db.refresh(client)
    return client


@router.patch("/clients/{client_id}/stage/next", response_model=ClientCard)
async def advance_stage(
    client_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_agent_or_above),
):
    """Advance client to the next stage in the funnel."""
    client = await _get_client_or_404(client_id, db, current_user)

    try:
        idx = LEAD_STAGE_ORDER.index(client.lead_stage)
        next_stage = LEAD_STAGE_ORDER[idx + 1]
    except (ValueError, IndexError):
        raise HTTPException(status_code=400, detail="No next stage available")

    client.lead_stage = next_stage
    client.updated_at = datetime.now(timezone.utc)

    interaction = Interaction(
        client_id=client.id,
        agent_id=current_user.id,
        interaction_type=InteractionType.note,
        content=f"Avanzado a etapa: {next_stage.value}",
    )
    db.add(interaction)
    await db.commit()
    await db.refresh(client)
    return client


# ─── Interaction log ───────────────────────────────────────────────────────────
@router.post("/clients/{client_id}/interactions", response_model=InteractionOut, status_code=status.HTTP_201_CREATED)
async def add_interaction(
    client_id: uuid.UUID,
    body: InteractionIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_agent_or_above),
):
    """Add a note, call log, or any interaction record to a client."""
    await _get_client_or_404(client_id, db, current_user)  # access check

    interaction = Interaction(
        client_id=client_id,
        agent_id=current_user.id,
        interaction_type=body.interaction_type,
        content=body.content,
    )
    db.add(interaction)
    await db.commit()
    await db.refresh(interaction)
    return interaction


@router.get("/clients/{client_id}/interactions", response_model=list[InteractionOut])
async def list_interactions(
    client_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_agent_or_above),
):
    """List all interactions for a client, newest first."""
    await _get_client_or_404(client_id, db, current_user)  # access check

    stmt = (
        select(Interaction)
        .where(Interaction.client_id == client_id)
        .order_by(Interaction.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


# ─── Client summary ────────────────────────────────────────────────────────────
@router.get("/clients/{client_id}/summary", response_model=ClientSummary)
async def client_summary(
    client_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_agent_or_above),
):
    """Return client card + last 10 interactions + total interaction count."""
    client = await _get_client_or_404(client_id, db, current_user)

    recent_stmt = (
        select(Interaction)
        .where(Interaction.client_id == client_id)
        .order_by(Interaction.created_at.desc())
        .limit(10)
    )
    recent = (await db.execute(recent_stmt)).scalars().all()

    count_stmt = select(func.count()).select_from(Interaction).where(Interaction.client_id == client_id)
    total = (await db.execute(count_stmt)).scalar_one()

    return ClientSummary(client=client, recent_interactions=recent, total_interactions=total)
