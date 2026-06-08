"""
predictor.py — Lead scoring inference.

Loads the trained XGBoost model (if available) and scores a client.
Falls back to a deterministic rule-based score when no model exists,
so the endpoint always returns a usable score during cold start.
"""
import structlog
from dataclasses import dataclass

from app.ml.features import ClientFeatures, FEATURE_NAMES
from app.ml.trainer import load_model, MODEL_PATH

log = structlog.get_logger()

_cached_model = None
_model_mtime: float = 0.0


def _get_model():
    """Load model with mtime-based cache invalidation."""
    global _cached_model, _model_mtime
    if not MODEL_PATH.exists():
        return None
    mtime = MODEL_PATH.stat().st_mtime
    if _cached_model is None or mtime != _model_mtime:
        _cached_model = load_model()
        _model_mtime = mtime
        log.info("predictor.model_loaded")
    return _cached_model


def _rule_based_score(features: ClientFeatures) -> float:
    """
    Heuristic score in [0, 1] when no trained model is available.
    Based on stage progression, recency of interaction, and visit activity.
    """
    stage_score = max(features.lead_stage_ordinal, 0) / 5.0  # 0..1
    recency = max(0.0, 1.0 - features.days_since_last_interaction / 30.0)
    visit_bonus = min(features.interactions_visit * 0.10, 0.30)
    call_bonus = min(features.interactions_call * 0.05, 0.15)
    event_bonus = min(features.num_scheduled_events * 0.05, 0.10)

    score = stage_score * 0.50 + recency * 0.25 + visit_bonus + call_bonus + event_bonus
    return round(min(max(score, 0.0), 1.0), 4)


@dataclass
class ScoreResult:
    score: float           # probability of closing [0, 1]
    label: str             # "hot" / "warm" / "cold"
    model_used: str        # "xgboost" | "rule_based"
    top_features: list[tuple[str, float]]  # top 5 feature importances (XGBoost only)


def _label(score: float) -> str:
    if score >= 0.65:
        return "hot"
    if score >= 0.35:
        return "warm"
    return "cold"


def score_lead(features: ClientFeatures) -> ScoreResult:
    """Score a single lead from its feature vector."""
    model = _get_model()

    if model is None:
        score = _rule_based_score(features)
        return ScoreResult(
            score=score,
            label=_label(score),
            model_used="rule_based",
            top_features=[],
        )

    import numpy as np
    X = np.array([features.to_list()], dtype=np.float32)
    prob = float(model.predict_proba(X)[0][1])

    # Extract top-5 feature importances
    try:
        importances = model.feature_importances_
        ranked = sorted(zip(FEATURE_NAMES, importances), key=lambda x: x[1], reverse=True)[:5]
    except Exception:
        ranked = []

    return ScoreResult(
        score=round(prob, 4),
        label=_label(prob),
        model_used="xgboost",
        top_features=ranked,
    )
