"""
matching.py — Semantic property matching endpoints.

GET  /matching/clients/{id}/properties     — top matches for a client (uses preference_embedding)
PATCH /matching/clients/{id}/preferences   — set/update client preferences + re-embed
POST /matching/query                       — free-text property search (agent tool)
"""
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_agent_or_above
from app.core.database import get_db
from app.matching.property_matcher import match_for_client, match_by_query, PropertyMatch
from app.matching.preference_embedder import update_client_preference_embedding

router = APIRouter(prefix="/matching", tags=["matching"])


# ─── Schemas ──────────────────────────────────────────────────────────────────
class PropertyMatchOut(BaseModel):
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


class PreferencesIn(BaseModel):
    operation_type: str | None = None
    property_type: str | None = None
    neighborhood: str | None = None
    city: str | None = None
    max_price: float | None = None
    currency: str = "USD"
    min_rooms: int | None = None
    min_sqm: float | None = None
    notes: str | None = Field(None, max_length=500)


class QueryMatchIn(BaseModel):
    query: str = Field(..., min_length=5, max_length=500)
    top_k: int = Field(10, ge=1, le=50)
    operation_type: str | None = None
    property_type: str | None = None
    max_price: float | None = None
    min_rooms: int | None = None


# ─── Routes ────────────────────────────────────────────────────────────────────
@router.get("/clients/{client_id}/properties", response_model=list[PropertyMatchOut])
async def get_client_matches(
    client_id: uuid.UUID,
    top_k: int = Query(10, ge=1, le=50),
    operation_type: str | None = Query(None),
    property_type: str | None = Query(None),
    max_price: float | None = Query(None),
    min_rooms: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _: Any = Depends(require_agent_or_above),
):
    """Return top property matches for a client based on their stored preference embedding."""
    filters = {
        k: v for k, v in {
            "operation_type": operation_type,
            "property_type": property_type,
            "max_price": max_price,
            "min_rooms": min_rooms,
        }.items() if v is not None
    }
    matches = await match_for_client(str(client_id), db, top_k=top_k, **filters)
    return matches


@router.patch("/clients/{client_id}/preferences", status_code=200)
async def set_preferences(
    client_id: uuid.UUID,
    body: PreferencesIn,
    db: AsyncSession = Depends(get_db),
    _: Any = Depends(require_agent_or_above),
):
    """Store client preferences and (re)generate their preference embedding."""
    updated = await update_client_preference_embedding(
        str(client_id),
        body.model_dump(exclude_none=True),
        db,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Client not found or empty preferences")
    return {"updated": True, "client_id": str(client_id)}


@router.post("/query", response_model=list[PropertyMatchOut])
async def query_properties(
    body: QueryMatchIn,
    db: AsyncSession = Depends(get_db),
    _: Any = Depends(require_agent_or_above),
):
    """Free-text semantic property search. Used by the ReAct agent's search_properties tool."""
    filters = {
        k: v for k, v in {
            "operation_type": body.operation_type,
            "property_type": body.property_type,
            "max_price": body.max_price,
            "min_rooms": body.min_rooms,
        }.items() if v is not None
    }
    return await match_by_query(body.query, db, top_k=body.top_k, **filters)
