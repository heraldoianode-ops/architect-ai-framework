import uuid
import enum
from datetime import datetime
from sqlalchemy import DateTime, Enum as PGEnum, ForeignKey, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class InteractionType(str, enum.Enum):
    note = "note"
    call = "call"
    whatsapp = "whatsapp"
    email = "email"
    visit = "visit"
    meeting = "meeting"


class Interaction(Base):
    __tablename__ = "interactions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    interaction_type: Mapped[InteractionType] = mapped_column(PGEnum(InteractionType, name="interaction_type_enum"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"), index=True)

    client = relationship("Client", back_populates="interactions", lazy="raise")
    agent = relationship("User", lazy="raise")
