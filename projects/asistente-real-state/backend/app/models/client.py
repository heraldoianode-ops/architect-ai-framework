import uuid
import enum
from sqlalchemy import String, Numeric, SmallInteger, Text, ARRAY, Enum as SAEnum, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector
from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.user import UserRole
from app.models.property import PropertyType


class LeadStage(str, enum.Enum):
    nuevo = "nuevo"
    contactado = "contactado"
    interesado = "interesado"
    visita_agendada = "visita_agendada"
    oferta_realizada = "oferta_realizada"
    negociacion = "negociacion"
    cerrado_ganado = "cerrado_ganado"
    cerrado_perdido = "cerrado_perdido"


class Client(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "clients"

    agent_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    # Identity
    full_name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str | None] = mapped_column(String, nullable=True)
    phone: Mapped[str | None] = mapped_column(String, nullable=True)
    whatsapp_id: Mapped[str | None] = mapped_column(String, unique=True, nullable=True, index=True)

    # Profile
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole, name="user_role", create_type=False), nullable=False, default=UserRole.cliente_comprador)
    source: Mapped[str | None] = mapped_column(String, nullable=True)

    # Buyer preferences (semantic matching)
    search_zones: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    search_types: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    budget_min: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    budget_max: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    preferences_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    preference_embedding: Mapped[list | None] = mapped_column(Vector(768), nullable=True)

    # Pipeline
    stage: Mapped[LeadStage] = mapped_column(SAEnum(LeadStage, name="lead_stage", create_type=False), default=LeadStage.nuevo, nullable=False, index=True)
    score: Mapped[int] = mapped_column(SmallInteger, default=0)
    closing_prob: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)

    # Tags & notes
    tags: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    metadata_: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
