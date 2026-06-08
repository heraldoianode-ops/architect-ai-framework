"""
test_predictions.py — L2 unit tests for Node 5.1: XGBoost lead scoring.
Tests: feature extraction, rule-based fallback, label thresholds, trainer data building.
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

from app.ml.features import (
    ClientFeatures, extract_features, FEATURE_NAMES,
    _STAGE_ORDINAL, _SOURCE_ORDINAL,
)
from app.ml.predictor import _rule_based_score, _label, score_lead


# ─── Feature vector shape ─────────────────────────────────────────────────────────
def test_feature_vector_length_matches_names():
    f = ClientFeatures()
    assert len(f.to_list()) == len(FEATURE_NAMES)


def test_all_feature_values_are_floats():
    f = ClientFeatures(days_since_created=5.0, total_interactions=3)
    for v in f.to_list():
        assert isinstance(v, float)


# ─── extract_features ───────────────────────────────────────────────────────────
def _make_client(stage="contactado", source="whatsapp", email="a@b.com", phone="123"):
    from app.models.client import LeadStage
    now = datetime.now(timezone.utc)
    c = MagicMock()
    c.lead_stage = LeadStage(stage)
    c.source = source
    c.email = email
    c.phone = phone
    c.preference_embedding = None
    c.created_at = now - timedelta(days=10)
    c.updated_at = now - timedelta(days=2)
    return c


def _make_interaction(itype="call", days_ago=3):
    from app.models.interaction import InteractionType
    i = MagicMock()
    i.interaction_type = InteractionType(itype)
    i.created_at = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return i


class TestExtractFeatures:
    def test_basic_extraction(self):
        client = _make_client(stage="calificado")
        feats = extract_features(client, [], [])
        assert feats.lead_stage_ordinal == _STAGE_ORDINAL["calificado"]
        assert feats.total_interactions == 0
        assert feats.has_email == 1
        assert feats.has_phone == 1

    def test_interaction_counts(self):
        client = _make_client()
        interactions = [
            _make_interaction("call", 1),
            _make_interaction("call", 2),
            _make_interaction("visit", 3),
            _make_interaction("note", 4),
        ]
        feats = extract_features(client, interactions, [])
        assert feats.total_interactions == 4
        assert feats.interactions_call == 2
        assert feats.interactions_visit == 1
        assert feats.interactions_note == 1

    def test_days_since_last_interaction(self):
        client = _make_client()
        interactions = [_make_interaction("whatsapp", 5)]
        feats = extract_features(client, interactions, [])
        assert 4.5 <= feats.days_since_last_interaction <= 5.5

    def test_no_interactions_gives_999(self):
        client = _make_client()
        feats = extract_features(client, [], [])
        assert feats.days_since_last_interaction == 999.0

    def test_event_count(self):
        client = _make_client()
        events = [MagicMock(), MagicMock()]
        feats = extract_features(client, [], events)
        assert feats.num_scheduled_events == 2

    def test_source_ordinal_unknown_defaults_to_4(self):
        client = _make_client(source="unknown_source")
        feats = extract_features(client, [], [])
        assert feats.source_ordinal == 4

    def test_preference_embedding_flag(self):
        client = _make_client()
        client.preference_embedding = [0.1] * 768
        feats = extract_features(client, [], [])
        assert feats.has_preference_embedding == 1

    def test_no_email_no_phone(self):
        client = _make_client(email=None, phone=None)
        feats = extract_features(client, [], [])
        assert feats.has_email == 0
        assert feats.has_phone == 0

    def test_interaction_velocity_positive(self):
        client = _make_client()
        interactions = [_make_interaction("call", i) for i in range(1, 6)]
        feats = extract_features(client, interactions, [])
        assert feats.interaction_velocity > 0


# ─── _rule_based_score ──────────────────────────────────────────────────────────
class TestRuleBasedScore:
    def test_returns_float_in_range(self):
        f = ClientFeatures()
        score = _rule_based_score(f)
        assert 0.0 <= score <= 1.0

    def test_higher_stage_higher_score(self):
        f_nuevo = ClientFeatures(lead_stage_ordinal=0, days_since_last_interaction=5)
        f_negoc = ClientFeatures(lead_stage_ordinal=4, days_since_last_interaction=5)
        assert _rule_based_score(f_negoc) > _rule_based_score(f_nuevo)

    def test_recent_interaction_boosts_score(self):
        f_stale = ClientFeatures(lead_stage_ordinal=2, days_since_last_interaction=60)
        f_fresh = ClientFeatures(lead_stage_ordinal=2, days_since_last_interaction=1)
        assert _rule_based_score(f_fresh) > _rule_based_score(f_stale)

    def test_visits_boost_score(self):
        f_no_visit = ClientFeatures(lead_stage_ordinal=2, days_since_last_interaction=5)
        f_visits = ClientFeatures(lead_stage_ordinal=2, days_since_last_interaction=5, interactions_visit=3)
        assert _rule_based_score(f_visits) > _rule_based_score(f_no_visit)


# ─── _label thresholds ────────────────────────────────────────────────────────────
@pytest.mark.parametrize("score,expected", [
    (0.80, "hot"),
    (0.65, "hot"),
    (0.64, "warm"),
    (0.35, "warm"),
    (0.34, "cold"),
    (0.00, "cold"),
])
def test_label_thresholds(score, expected):
    assert _label(score) == expected


# ─── score_lead — no model path ───────────────────────────────────────────────────
def test_score_lead_uses_rule_based_when_no_model():
    with patch("app.ml.predictor._get_model", return_value=None):
        f = ClientFeatures(lead_stage_ordinal=3, days_since_last_interaction=2, interactions_visit=1)
        result = score_lead(f)
    assert result.model_used == "rule_based"
    assert 0.0 <= result.score <= 1.0
    assert result.label in ("hot", "warm", "cold")
