import uuid
import enum
from typing import Optional
from sqlalchemy import String, Numeric, SmallInteger, Boolean, Date, ARRAY, Enum as SAEnum, JSON, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector
from app.models.base import Base, TimestampMixin, UUIDMixin


class PropertyType(str, enum.Enum):
    departamento = "departamento"
    casa = "casa"
    ph = "ph"
    local = "local"
    oficina = "oficina"
    terreno = "terreno"
    cochera = "cochera"
    galpon = "galpon"
    otro = "otro"


class OperationType(str, enum.Enum):
    venta = "venta"
    alquiler = "alquiler"
    alquiler_temporario = "alquiler_temporario"


class PropertyStatus(str, enum.Enum):
    disponible = "disponible"
    reservada = "reservada"
    vendida = "vendida"
    alquilada = "alquilada"
    en_negociacion = "en_negociacion"
    pausada = "pausada"
    eliminada = "eliminada"


class Property(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "properties"

    agent_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    # Source
    external_id: Mapped[str | None] = mapped_column(String, nullable=True)
    source: Mapped[str] = mapped_column(String, default="manual")

    # Location
    address: Mapped[str] = mapped_column(String, nullable=False)
    neighborhood: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    city: Mapped[str] = mapped_column(String, default="Buenos Aires")
    province: Mapped[str] = mapped_column(String, default="CABA")
    country: Mapped[str] = mapped_column(String, default="Argentina")
    latitude: Mapped[float | None] = mapped_column(nullable=True)
    longitude: Mapped[float | None] = mapped_column(nullable=True)

    # Specs
    property_type: Mapped[PropertyType] = mapped_column(SAEnum(PropertyType, name="property_type", create_type=False), nullable=False, index=True)
    operation_type: Mapped[OperationType] = mapped_column(SAEnum(OperationType, name="operation_type", create_type=False), nullable=False, index=True)
    price: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True, index=True)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    expenses: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    sqm_total: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)
    sqm_covered: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)
    rooms: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    bedrooms: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    bathrooms: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    parking: Mapped[int] = mapped_column(SmallInteger, default=0)
    floor: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    amenities: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)

    # Status
    status: Mapped[PropertyStatus] = mapped_column(SAEnum(PropertyStatus, name="property_status", create_type=False), default=PropertyStatus.disponible, nullable=False, index=True)
    listed_at: Mapped[str | None] = mapped_column(Date, nullable=True)

    # Content
    title: Mapped[str | None] = mapped_column(String, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    photos: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)

    # Vector (semantic matching)
    embedding: Mapped[list | None] = mapped_column(Vector(768), nullable=True)

    metadata_: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
