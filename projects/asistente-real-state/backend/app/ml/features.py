"""
features.py — Feature extraction for lead scoring.
Builds a flat numeric feature vector from a client + their interactions + events.
All features are domain-meaningful and interpretable.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Sequence

# Lead stage → ordinal (higher = further in funnel)
_STAGE_ORDINAL = {
    "nuevo": 0,
    "contactado": 1,
    "calificado": 2,
    "propuesta": 3,
    "negociacion": 4,
    "cerrado": 5,
    "perdido": -1,
}

_SOURCE_ORDINAL = {
    "whatsapp": 0,
    "adinco": 1,
    "excel": 2,
    "google_drive": 3,
    "manual": 4,
}

FEATURE_NAMES = [
    "days_since_created",
    "days_since_last_interaction",
    "total_interactions",
    "interactions_note",
    "interactions_call",
    "interactions_whatsapp",
    "interactions_email",
    "interactions_visit",
    "interactions_meeting",
    "lead_stage_ordinal",
    "has_preference_embedding",
    "num_scheduled_events",
    "source_ordinal",
    "days_in_current_stage",
    "interaction_velocity",   # interactions per day since created
    "has_email",
    "has_phone",
]


@dataclass
class ClientFeatures:
    days_since_created: float = 0.0
    days_since_last_interaction: float = 999.0
    total_interactions: int = 0
    interactions_note: int = 0
    interactions_call: int = 0
    interactions_whatsapp: int = 0
    interactions_email: int = 0
    interactions_visit: int = 0
    interactions_meeting: int = 0
    lead_stage_ordinal: int = 0
    has_preference_embedding: int = 0
    num_scheduled_events: int = 0
    source_ordinal: int = 4
    days_in_current_stage: float = 0.0
    interaction_velocity: float = 0.0
    has_email: int = 0
    has_phone: int = 0

    def to_list(self) -> list[float]:
        return [float(v) for v in asdict(self).values()]


def extract_features(
    client,
    interactions: Sequence,
    events: Sequence,
    now: datetime | None = None,
) -> ClientFeatures:
    """
    Extract a ClientFeatures vector from ORM objects.
    `interactions` and `events` are pre-loaded lists (no lazy loads here).
    """
    now = now or datetime.now(timezone.utc)

    # Ensure timezone-aware comparison
    created_at = client.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    updated_at = client.updated_at
    if updated_at.tzinfo is None:
        updated_at = updated_at.replace(tzinfo=timezone.utc)

    days_since_created = max((now - created_at).total_seconds() / 86400, 0)
    days_in_current_stage = max((now - updated_at).total_seconds() / 86400, 0)

    # Interaction stats
    type_counts: dict[str, int] = {
        "note": 0, "call": 0, "whatsapp": 0,
        "email": 0, "visit": 0, "meeting": 0,
    }
    latest_interaction_ts: datetime | None = None

    for interaction in interactions:
        itype = interaction.interaction_type.value if hasattr(interaction.interaction_type, 'value') else str(interaction.interaction_type)
        if itype in type_counts:
            type_counts[itype] += 1
        ts = interaction.created_at
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        if latest_interaction_ts is None or ts > latest_interaction_ts:
            latest_interaction_ts = ts

    total = sum(type_counts.values())
    days_since_last = (
        (now - latest_interaction_ts).total_seconds() / 86400
        if latest_interaction_ts else 999.0
    )
    velocity = total / days_since_created if days_since_created > 0 else 0.0

    stage_str = client.lead_stage.value if hasattr(client.lead_stage, 'value') else str(client.lead_stage)
    source_str = (client.source or "").lower()

    return ClientFeatures(
        days_since_created=round(days_since_created, 2),
        days_since_last_interaction=round(days_since_last, 2),
        total_interactions=total,
        interactions_note=type_counts["note"],
        interactions_call=type_counts["call"],
        interactions_whatsapp=type_counts["whatsapp"],
        interactions_email=type_counts["email"],
        interactions_visit=type_counts["visit"],
        interactions_meeting=type_counts["meeting"],
        lead_stage_ordinal=_STAGE_ORDINAL.get(stage_str, 0),
        has_preference_embedding=1 if getattr(client, 'preference_embedding', None) is not None else 0,
        num_scheduled_events=len(events),
        source_ordinal=_SOURCE_ORDINAL.get(source_str, 4),
        days_in_current_stage=round(days_in_current_stage, 2),
        interaction_velocity=round(velocity, 4),
        has_email=1 if client.email else 0,
        has_phone=1 if client.phone else 0,
    )
