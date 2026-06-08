"""
property_matcher.py — Semantic ANN matching engine.

Two search modes:
  1. client_match(client_id)  — use stored preference_embedding
  2. query_match(text)        — embed ad-hoc text query, return similar properties

Both use pgvector cosine distance on properties.embedding.
"""
import structlog
from dataclasses import dataclass
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.property import Property
from app.models.client import Client
from app.rag.embedder import embed_text

log = structlog.get_logger()

DEFAULT_TOP_K = 10
MIN_SIMILARITY = 0.30


@dataclass
class PropertyMatch:
    property_id: str
    address: str
    neighborhood: str | None
    city: str
    property_type: str
    operation_type: str
    price: float | None
    currency: str
    rooms: int | None
    sqm_total: float | None
    title: str
    similarity: float


def build_property_text(prop: Property) -> str:
    """
    Compose a natural-language description of a property for embedding.
    Consistent field order maximises semantic coherence.
    """
    parts = [
        f"{prop.operation_type} {prop.property_type}",
        f"en {prop.neighborhood}" if prop.neighborhood else "",
        prop.city,
        f"{prop.currency} {int(prop.price):,}" if prop.price else "",
        f"{prop.rooms} ambientes" if prop.rooms else "",
        f"{int(prop.sqm_total)} m2" if prop.sqm_total else "",
        prop.title or "",
        (prop.description or "")[:300],
    ]
    return " ".join(p for p in parts if p).strip()


async def _ann_search(
    query_vector: list[float],
    db: AsyncSession,
    top_k: int,
    operation_type: str | None = None,
    property_type: str | None = None,
    max_price: float | None = None,
    min_rooms: int | None = None,
) -> list[PropertyMatch]:
    """Core ANN query with optional hard filters applied after vector search."""
    distance_expr = Property.embedding.op("<=>")(
        text(f"'{query_vector}'::vector")
    )

    stmt = (
        select(
            Property.id,
            Property.address,
            Property.neighborhood,
            Property.city,
            Property.property_type,
            Property.operation_type,
            Property.price,
            Property.currency,
            Property.rooms,
            Property.sqm_total,
            Property.title,
            (1 - distance_expr).label("similarity"),
        )
        .where(Property.embedding.is_not(None))
        .order_by(distance_expr)
        .limit(top_k * 3)  # over-fetch before hard filters
    )

    rows = (await db.execute(stmt)).all()

    matches: list[PropertyMatch] = []
    for row in rows:
        sim = float(row.similarity)
        if sim < MIN_SIMILARITY:
            continue
        if operation_type and row.operation_type != operation_type:
            continue
        if property_type and row.property_type != property_type:
            continue
        if max_price and row.price and row.price > max_price:
            continue
        if min_rooms and row.rooms and row.rooms < min_rooms:
            continue
        matches.append(PropertyMatch(
            property_id=str(row.id),
            address=row.address,
            neighborhood=row.neighborhood,
            city=row.city,
            property_type=row.property_type,
            operation_type=row.operation_type,
            price=row.price,
            currency=row.currency,
            rooms=row.rooms,
            sqm_total=row.sqm_total,
            title=row.title or row.address,
            similarity=sim,
        ))
        if len(matches) >= top_k:
            break

    return matches


async def match_for_client(
    client_id: str,
    db: AsyncSession,
    top_k: int = DEFAULT_TOP_K,
    **filters,
) -> list[PropertyMatch]:
    """
    Find properties matching a client’s stored preference_embedding.
    Returns empty list if client has no preference embedding yet.
    """
    from uuid import UUID
    result = await db.execute(select(Client).where(Client.id == UUID(client_id)))
    client = result.scalar_one_or_none()

    if not client or client.preference_embedding is None:
        log.info("matcher.no_preference_embedding", client_id=client_id)
        return []

    return await _ann_search(client.preference_embedding, db, top_k, **filters)


async def match_by_query(
    query_text: str,
    db: AsyncSession,
    top_k: int = DEFAULT_TOP_K,
    **filters,
) -> list[PropertyMatch]:
    """Embed a free-text query and find matching properties."""
    vector = await embed_text(query_text)
    return await _ann_search(vector, db, top_k, **filters)
