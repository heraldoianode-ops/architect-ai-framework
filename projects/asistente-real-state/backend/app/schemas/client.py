import uuid
from pydantic import BaseModel, Field
from app.models.client import LeadStage
from app.models.user import UserRole
from app.models.property import PropertyType


class ClientCreate(BaseModel):
    full_name: str
    email: str | None = None
    phone: str | None = None
    whatsapp_id: str | None = None
    role: UserRole = UserRole.cliente_comprador
    source: str | None = None
    search_zones: list[str] | None = None
    search_types: list[PropertyType] | None = None
    budget_min: float | None = None
    budget_max: float | None = None
    preferences_text: str | None = None
    tags: list[str] | None = None
    notes: str | None = None


class ClientUpdate(BaseModel):
    full_name: str | None = None
    phone: str | None = None
    stage: LeadStage | None = None
    score: int | None = Field(default=None, ge=0, le=100)
    search_zones: list[str] | None = None
    budget_min: float | None = None
    budget_max: float | None = None
    preferences_text: str | None = None
    tags: list[str] | None = None
    notes: str | None = None


class ClientRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    agent_id: uuid.UUID | None
    full_name: str
    email: str | None
    phone: str | None
    whatsapp_id: str | None
    role: UserRole
    stage: LeadStage
    score: int
    closing_prob: float | None
    search_zones: list[str] | None
    budget_min: float | None
    budget_max: float | None
    tags: list[str] | None
    notes: str | None
    source: str | None
