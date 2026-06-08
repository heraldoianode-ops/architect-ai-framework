import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_user, require_agent_or_above
from app.models.user import User, UserRole
from app.models.client import Client
from app.schemas.client import ClientCreate, ClientUpdate, ClientRead

router = APIRouter(prefix="/clients", tags=["clients"])


@router.get("", response_model=list[ClientRead])
async def list_clients(
    stage: str | None = Query(None),
    query: str | None = Query(None),
    limit: int = Query(20, le=100),
    offset: int = Query(0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_agent_or_above),
):
    stmt = select(Client)
    filters = []

    # Agents see only their clients; brokers/admin see all
    if current_user.role == UserRole.agente_real_state:
        filters.append(Client.agent_id == current_user.id)
    if stage:
        filters.append(Client.stage == stage)
    if query:
        filters.append(Client.full_name.ilike(f"%{query}%"))

    if filters:
        stmt = stmt.where(and_(*filters))

    stmt = stmt.order_by(Client.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("", response_model=ClientRead, status_code=status.HTTP_201_CREATED)
async def create_client(
    body: ClientCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_agent_or_above),
):
    client = Client(**body.model_dump(), agent_id=current_user.id)
    db.add(client)
    await db.flush()
    return client


@router.get("/{client_id}", response_model=ClientRead)
async def get_client(
    client_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_agent_or_above),
):
    result = await db.execute(select(Client).where(Client.id == client_id))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return client


@router.patch("/{client_id}", response_model=ClientRead)
async def update_client(
    client_id: uuid.UUID,
    body: ClientUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_agent_or_above),
):
    result = await db.execute(select(Client).where(Client.id == client_id))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(client, field, value)
    return client
