import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, Enum as PGEnum, String, JSON, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
import enum


class SourceType(str, enum.Enum):
    adinco = "adinco"
    google_drive = "google_drive"
    excel = "excel"


class ScrapingSource(Base):
    __tablename__ = "scraping_sources"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    source_type: Mapped[SourceType] = mapped_column(PGEnum(SourceType, name="source_type_enum"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_run_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"), onupdate=lambda: datetime.now(timezone.utc))
