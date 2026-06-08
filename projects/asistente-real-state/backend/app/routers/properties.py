import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_user, require_agent_or_above
from app.models.user import User
from app.models.property import Property, PropertyStatus
from app.schemas.property import PropertyCreate, PropertyUpdate, PropertyRead, PropertyFilters

router = APIRouter(prefix="/properties", tags=["properties"])


@router.get("", response_model=list[PropertyRead])
async def list_properties(
    operation_type: str | None = Query(None),
    property_type: str | None = Query(None),
    neighborhood: str | None = Query(None),
    price_min: float | None = Query(None),
    price_max: float | None = Query(None),
    bedrooms: int | None = Query(None),
    status: str | None = Query(None),
    query: str | None = Query(None, description="Full-text search"),
    limit: int = Query(20, le=100),
    offset: int = Query(0),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    stmt = select(Property)
    filters = []

    if operation_type:
        filters.append(Property.operation_type == operation_type)
    if property_type:
        filters.append(Property.property_type == property_type)
    if neighborhood:
        filters.append(Property.neighborhood.ilike(f"%{neighborhood}%"))
    if price_min is not None:
        filters.append(Property.price >= price_min)
    if price_max is not None:
        filters.append(Property.price <= price_max)
    if bedrooms is not None:
        filters.append(Property.bedrooms >= bedrooms)
    if status:
        filters.append(Property.status == status)
    if query:
        # PostgreSQL full-text search
        filters.append(
            func.to_tsvector("spanish", func.coalesce(Property.title, "") + " " + func.coalesce(Property.description, "") + " " + Property.address)
            .op("@@")(func.plainto_tsquery("spanish", query))
        )

    if filters:
        stmt = stmt.where(and_(*filters))

    stmt = stmt.where(Property.status != PropertyStatus.eliminada)
    stmt = stmt.order_by(Property.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("", response_model=PropertyRead, status_code=status.HTTP_201_CREATED)
async def create_property(
    body: PropertyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_agent_or_above),
):
    prop = Property(**body.model_dump(), agent_id=current_user.id)
    db.add(prop)
    await db.flush()
    return prop


@router.get("/{property_id}", response_model=PropertyRead)
async def get_property(
    property_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(Property).where(Property.id == property_id))
    prop = result.scalar_one_or_none()
    if not prop:
        raise HTTPException(status_code=404, detail="Propiedad no encontrada")
    return prop


@router.patch("/{property_id}", response_model=PropertyRead)
async def update_property(
    property_id: uuid.UUID,
    body: PropertyUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_agent_or_above),
):
    result = await db.execute(select(Property).where(Property.id == property_id))
    prop = result.scalar_one_or_none()
    if not prop:
        raise HTTPException(status_code=404, detail="Propiedad no encontrada")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(prop, field, value)
    return prop


@router.delete("/{property_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_property(
    property_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_agent_or_above),
):
    result = await db.execute(select(Property).where(Property.id == property_id))
    prop = result.scalar_one_or_none()
    if not prop:
        raise HTTPException(status_code=404, detail="Propiedad no encontrada")
    prop.status = PropertyStatus.eliminada
