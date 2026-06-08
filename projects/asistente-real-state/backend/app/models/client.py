import uuid
import enum
from datetime import datetime
from sqlalchemy import DateTime, Enum as PGEnum, ForeignKey, String, Text, text, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector
from app.core.database import Base


class LeadStage(str, enum.Enum):
    nuevo = "nuevo"
    contactado = "contactado"
    calificado = "calificado"
    propuesta = "propuesta"
    negociacion = "negociacion"
    cerrado = "cerrado"
    perdido = "perdido"


LEAD_STAGE_ORDER = [
    LeadStage.nuevo,
    LeadStage.contactado,
    LeadStage.calificado,
    LeadStage.propuesta,
    LeadStage.negociacion,
    LeadStage.cerrado,
]


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    agent_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str | None] = mapped_column(String(254), nullable=True, unique=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True, unique=True)
    source: Mapped[str | None] = mapped_column(String(60), nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    lead_stage: Mapped[LeadStage] = mapped_column(PGEnum(LeadStage, name="lead_stage_enum"), nullable=False, default=LeadStage.nuevo, index=True)
    preference_embedding: Mapped[list | None] = mapped_column(Vector(768), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))

    agent = relationship("User", lazy="raise")
    interactions = relationship("Interaction", back_populates="client", lazy="raise", order_by="Interaction.created_at.desc()")

    __table_args__ = (
        Index(
            "ix_clients_fts",
            text("to_tsvector('spanish', coalesce(full_name,'') || ' ' || coalesce(email,'') || ' ' || coalesce(notes,''))"),
            postgresql_using="gin",
        ),
    )
