"""
search_properties tool — searches the property database with natural language filters.
The agent calls this when a client asks "busco departamento 2 amb en Palermo hasta 200k".
"""
from langchain_core.tools import tool
from sqlalchemy import select, and_
from app.core.database import AsyncSessionLocal
from app.models.property import Property, PropertyStatus


@tool
async def search_properties(
    operation_type: str = "",
    property_type: str = "",
    neighborhood: str = "",
    price_max: float = 0,
    price_min: float = 0,
    bedrooms: int = 0,
    limit: int = 5,
) -> str:
    """
    Search available properties in the database.
    Use when client asks about properties to buy or rent.
    Returns a formatted list of matching properties.

    Args:
        operation_type: 'venta' or 'alquiler' or 'alquiler_temporario'
        property_type: 'departamento', 'casa', 'ph', 'local', 'oficina', 'terreno', etc.
        neighborhood: neighborhood name (barrio), e.g. 'Palermo', 'Belgrano'
        price_max: maximum price in USD (0 = no limit)
        price_min: minimum price in USD (0 = no limit)
        bedrooms: minimum number of bedrooms (0 = any)
        limit: max results to return (default 5)
    """
    async with AsyncSessionLocal() as db:
        stmt = select(Property).where(Property.status == PropertyStatus.disponible)
        filters = []

        if operation_type:
            filters.append(Property.operation_type == operation_type)
        if property_type:
            filters.append(Property.property_type == property_type)
        if neighborhood:
            filters.append(Property.neighborhood.ilike(f"%{neighborhood}%"))
        if price_max > 0:
            filters.append(Property.price <= price_max)
        if price_min > 0:
            filters.append(Property.price >= price_min)
        if bedrooms > 0:
            filters.append(Property.bedrooms >= bedrooms)

        if filters:
            stmt = stmt.where(and_(*filters))

        stmt = stmt.order_by(Property.price.asc()).limit(limit)
        result = await db.execute(stmt)
        props = result.scalars().all()

    if not props:
        return "No encontré propiedades que coincidan con los criterios indicados."

    lines = [f"Encontré {len(props)} propiedad(es):\n"]
    for p in props:
        lines.append(
            f"• {p.title or p.address} — {p.property_type} en {p.neighborhood or p.city} "
            f"| {p.operation_type} USD {p.price:,.0f} "
            f"| {p.bedrooms or '?'} dorm / {p.bathrooms or '?'} baños / {p.sqm_covered or '?'} m² cub. "
            f"[ID: {str(p.id)[:8]}]"
        )
    return "\n".join(lines)
