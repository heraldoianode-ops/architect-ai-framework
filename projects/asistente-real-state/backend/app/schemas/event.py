import uuid
from datetime import datetime
from pydantic import BaseModel
from app.models.event import EventType, EventStatus


class EventCreate(BaseModel):
    client_id: uuid.UUID
    property_id: uuid.UUID | None = None
    event_type: EventType
    title: str
    description: str | None = None
    scheduled_at: datetime
    duration_min: int = 60
    location: str | None = None


class EventUpdate(BaseModel):
    status: EventStatus | None = None
    scheduled_at: datetime | None = None
    title: str | None = None
    description: str | None = None
    location: str | None = None
    duration_min: int | None = None


class EventRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    agent_id: uuid.UUID | None
    client_id: uuid.UUID | None
    property_id: uuid.UUID | None
    event_type: EventType
    status: EventStatus
    title: str
    description: str | None
    scheduled_at: datetime
    duration_min: int
    location: str | None
    reminder_24h_sent: bool
    reminder_1h_sent: bool
