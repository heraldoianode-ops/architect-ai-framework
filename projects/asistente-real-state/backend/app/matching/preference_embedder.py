"""
preference_embedder.py — Build and store a client’s preference embedding.

Converts structured or free-text preferences into a single embedding
stored in clients.preference_embedding for ANN matching.
"""
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.rag.embedder import embed_text

log = structlog.get_logger()


def build_preference_text(preferences: dict) -> str:
    """
    Convert a structured preferences dict into a natural-language description.
    Accepts any combination of keys; unknown keys are ignored gracefully.

    Example input:
      {"operation_type": "alquiler", "property_type": "departamento",
       "neighborhood": "Palermo", "max_price": 1200, "currency": "USD",
       "min_rooms": 2, "notes": "cerca del subte, luminoso"}
    """
    parts: list[str] = []

    op = preferences.get("operation_type", "")
    ptype = preferences.get("property_type", "")
    if op and ptype:
        parts.append(f"Busco {op} de {ptype}")
    elif op:
        parts.append(f"Busco para {op}")
    elif ptype:
        parts.append(f"Busco {ptype}")

    if preferences.get("neighborhood"):
        parts.append(f"en {preferences['neighborhood']}")
    if preferences.get("city"):
        parts.append(preferences["city"])

    price = preferences.get("max_price")
    currency = preferences.get("currency", "USD")
    if price:
        parts.append(f"presupuesto hasta {currency} {int(price):,}")

    rooms = preferences.get("min_rooms")
    if rooms:
        parts.append(f"mínimo {rooms} ambientes")

    sqm = preferences.get("min_sqm")
    if sqm:
        parts.append(f"mínimo {sqm} m2")

    notes = preferences.get("notes", "").strip()
    if notes:
        parts.append(notes)

    return ". ".join(parts) if parts else ""


async def update_client_preference_embedding(
    client_id: str,
    preferences: dict,
    db: AsyncSession,
) -> bool:
    """
    Build preference text, embed it, and store in client.preference_embedding.
    Returns True if updated, False if client not found or text is empty.
    """
    from uuid import UUID
    from app.models.client import Client
    from datetime import datetime, timezone

    pref_text = build_preference_text(preferences)
    if not pref_text:
        log.warning("preference_embedder.empty_text", client_id=client_id)
        return False

    result = await db.execute(select(Client).where(Client.id == UUID(client_id)))
    client = result.scalar_one_or_none()
    if not client:
        return False

    embedding = await embed_text(pref_text)
    client.preference_embedding = embedding
    client.updated_at = datetime.now(timezone.utc)
    await db.commit()

    log.info("preference_embedder.updated", client_id=client_id)
    return True


async def embed_property(
    property_id: str,
    db: AsyncSession,
) -> bool:
    """
    Build and store the embedding for a single property.
    Called by the Celery task after new property insertion.
    """
    from uuid import UUID
    from app.models.property import Property
    from app.matching.property_matcher import build_property_text

    result = await db.execute(select(Property).where(Property.id == UUID(property_id)))
    prop = result.scalar_one_or_none()
    if not prop:
        return False

    text = build_property_text(prop)
    if not text:
        return False

    prop.embedding = await embed_text(text)
    await db.commit()
    return True
