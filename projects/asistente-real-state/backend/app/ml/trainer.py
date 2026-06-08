"""
trainer.py — XGBoost lead scoring model training pipeline.

Target: binary classification
  1 = client reached "cerrado" within 90 days of creation
  0 = client reached "perdido" or still open after 90 days

Training data source: clients + interactions + events from the production DB.
Model artifact saved to MODEL_PATH (mounted volume in Docker).
"""
import os
import pickle
import structlog
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

log = structlog.get_logger()

MODEL_PATH = Path(os.environ.get("ML_MODEL_PATH", "/app/ml_models/lead_scorer.pkl"))
MIN_TRAINING_SAMPLES = 50   # don't train with fewer rows — not enough signal
CLOSED_WITHIN_DAYS = 90


def _build_training_data(clients, interactions_by_client, events_by_client):
    """
    Build (X, y) from labeled clients (cerrado=1, perdido=0).
    Clients still in intermediate stages are excluded from training.
    """
    from app.ml.features import extract_features

    X, y = [], []
    for client in clients:
        stage = client.lead_stage.value if hasattr(client.lead_stage, 'value') else str(client.lead_stage)
        if stage not in ("cerrado", "perdido"):
            continue

        label = 1 if stage == "cerrado" else 0
        interactions = interactions_by_client.get(str(client.id), [])
        events = events_by_client.get(str(client.id), [])

        # Simulate features as they were before the final stage transition
        features = extract_features(client, interactions, events)
        X.append(features.to_list())
        y.append(label)

    return np.array(X, dtype=np.float32), np.array(y, dtype=np.int32)


def train_model(X: np.ndarray, y: np.ndarray) -> object:
    """Train an XGBoost classifier and return the fitted model."""
    import xgboost as xgb

    pos = int(y.sum())
    neg = len(y) - pos
    scale_pos_weight = neg / pos if pos > 0 else 1.0

    model = xgb.XGBClassifier(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=scale_pos_weight,
        use_label_encoder=False,
        eval_metric="logloss",
        random_state=42,
    )
    model.fit(X, y)
    return model


def save_model(model, path: Path = MODEL_PATH):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        pickle.dump(model, f)
    log.info("trainer.model_saved", path=str(path))


def load_model(path: Path = MODEL_PATH):
    if not path.exists():
        return None
    with open(path, "rb") as f:
        return pickle.load(f)


async def run_training_pipeline(db) -> dict:
    """
    Full pipeline: load data from DB → build features → train → save.
    Returns a status dict.
    """
    from sqlalchemy import select
    from app.models.client import Client
    from app.models.interaction import Interaction
    from app.models.event import Event

    clients = (await db.execute(select(Client))).scalars().all()
    interactions = (await db.execute(select(Interaction))).scalars().all()
    events = (await db.execute(select(Event))).scalars().all()

    interactions_by_client: dict[str, list] = {}
    for i in interactions:
        key = str(i.client_id)
        interactions_by_client.setdefault(key, []).append(i)

    events_by_client: dict[str, list] = {}
    for e in events:
        if e.client_id:
            key = str(e.client_id)
            events_by_client.setdefault(key, []).append(e)

    X, y = _build_training_data(clients, interactions_by_client, events_by_client)

    if len(X) < MIN_TRAINING_SAMPLES:
        log.warning("trainer.insufficient_data", samples=len(X), required=MIN_TRAINING_SAMPLES)
        return {"status": "skipped", "reason": "insufficient_data", "samples": len(X)}

    model = train_model(X, y)
    save_model(model)

    return {
        "status": "ok",
        "samples": len(X),
        "positive": int(y.sum()),
        "negative": int(len(y) - y.sum()),
    }
