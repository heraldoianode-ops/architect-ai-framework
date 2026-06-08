import uuid
import enum
from datetime import datetime
from sqlalchemy import DateTime, Enum as PGEnum, ForeignKey, String, Text, text, Float, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class FeedbackTarget(str, enum.Enum):
    agent_response = "agent_response"   # bot reply quality
    property_match = "property_match"   # match relevance
    lead_score = "lead_score"           # score accuracy
    rag_chunk = "rag_chunk"             # chunk usefulness


class FeedbackSentiment(str, enum.Enum):
    positive = "positive"
    negative = "negative"
    neutral = "neutral"


class FeedbackRecord(Base):
    __tablename__ = "objection_feedback"  # reuse existing table from schema

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    target_type: Mapped[FeedbackTarget] = mapped_column(
        PGEnum(FeedbackTarget, name="feedback_target_enum"), nullable=False, index=True
    )
    target_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    agent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    sentiment: Mapped[FeedbackSentiment] = mapped_column(
        PGEnum(FeedbackSentiment, name="feedback_sentiment_enum"), nullable=False
    )
    score_override: Mapped[float | None] = mapped_column(Float, nullable=True)
    processed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"), index=True)
