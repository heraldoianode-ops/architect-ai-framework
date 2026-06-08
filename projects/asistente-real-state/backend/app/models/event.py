import uuid
import enum
from datetime import datetime
from sqlalchemy import String, SmallInteger, Boolean, Text, Enum as SAEnum, JSON, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import Base, TimestampMixin, UUIDMixin


class EventType(str, enum.Enum):
    visita_comprador = "visita_comprador"
    captacion_vendedor = "captacion_vendedor"
    reunion_agente = "reunion_agente"
    llamada = "llamada"
    otro = "otro"


class EventStatus(str, enum.Enum):
    pendiente = "pendiente"
    confirmado = "confirmado"
    realizado = "realizado"
    cancelado = "cancelado"
    reprogramado = "reprogramado"


class Event(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "events"

    agent_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    client_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=True, index=True)
    property_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("properties.id", ondelete="SET NULL"), nullable=True)

    event_type: Mapped[EventType] = mapped_column(SAEnum(EventType, name="event_type", create_type=False), nullable=False)
    status: Mapped[EventStatus] = mapped_column(SAEnum(EventStatus, name="event_status", create_type=False), default=EventStatus.pendiente, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    duration_min: Mapped[int] = mapped_column(SmallInteger, default=60)
    location: Mapped[str | None] = mapped_column(String, nullable=True)

    reminder_24h_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    reminder_1h_sent: Mapped[bool] = mapped_column(Boolean, default=False)

    metadata_: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
