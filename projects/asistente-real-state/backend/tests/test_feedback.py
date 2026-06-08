"""
test_feedback.py — L2 unit tests for Node 6.1: meta-learning feedback loop.
Tests: feedback model, processor logic, similarity adjustment, score corrections.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.feedback import FeedbackTarget, FeedbackSentiment
from app.ml.meta_learner import (
    NEGATIVE_RATE_THRESHOLD,
    MATCH_NEGATIVE_THRESHOLD,
    SIMILARITY_STEP,
    SIMILARITY_MIN,
    SIMILARITY_MAX,
)


# ─── Constants sanity ──────────────────────────────────────────────────────────
def test_thresholds_are_in_range():
    assert 0 < NEGATIVE_RATE_THRESHOLD < 1
    assert 0 < MATCH_NEGATIVE_THRESHOLD < 1
    assert 0 < SIMILARITY_MIN < SIMILARITY_MAX < 1
    assert 0 < SIMILARITY_STEP < 0.1


# ─── FeedbackTarget / FeedbackSentiment ─────────────────────────────────────────
def test_all_targets_defined():
    targets = {t.value for t in FeedbackTarget}
    assert "agent_response" in targets
    assert "property_match" in targets
    assert "lead_score" in targets
    assert "rag_chunk" in targets


def test_all_sentiments_defined():
    sentiments = {s.value for s in FeedbackSentiment}
    assert {"positive", "negative", "neutral"} == sentiments


# ─── process_agent_response_feedback ──────────────────────────────────────────
def _make_feedback(sentiment, target=FeedbackTarget.agent_response, score_override=None):
    r = MagicMock()
    r.id = "fake-id"
    r.sentiment = FeedbackSentiment(sentiment)
    r.target_type = target
    r.score_override = score_override
    r.target_id = "some-id"
    r.payload = {}
    return r


@pytest.mark.asyncio
async def test_agent_response_no_feedback_returns_zero():
    from app.ml.meta_learner import process_agent_response_feedback
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    db.execute = AsyncMock(return_value=mock_result)

    result = await process_agent_response_feedback(db)
    assert result["processed"] == 0


@pytest.mark.asyncio
async def test_agent_response_high_negative_rate_emits_alert():
    from app.ml.meta_learner import process_agent_response_feedback
    rows = [_make_feedback("negative")] * 4 + [_make_feedback("positive")] * 1

    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = rows
    db.execute = AsyncMock(return_value=mock_result)

    result = await process_agent_response_feedback(db)
    assert result["processed"] == 5
    assert result["negative_rate"] == 0.8
    assert "alert" in result


@pytest.mark.asyncio
async def test_agent_response_low_negative_rate_no_alert():
    from app.ml.meta_learner import process_agent_response_feedback
    rows = [_make_feedback("negative")] * 1 + [_make_feedback("positive")] * 9

    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = rows
    db.execute = AsyncMock(return_value=mock_result)

    result = await process_agent_response_feedback(db)
    assert "alert" not in result
    assert result["negative_rate"] == 0.1


# ─── process_match_feedback — similarity adjustment ─────────────────────────────
@pytest.mark.asyncio
async def test_match_feedback_raises_threshold_on_high_negative():
    from app.ml.meta_learner import process_match_feedback
    import app.rag.retriever as retriever_module
    import app.matching.property_matcher as matcher_module

    original = retriever_module.MIN_SIMILARITY
    rows = [_make_feedback("negative", FeedbackTarget.property_match)] * 4 + \
           [_make_feedback("positive", FeedbackTarget.property_match)] * 1

    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = rows
    db.execute = AsyncMock(return_value=mock_result)

    result = await process_match_feedback(db)
    assert result["action"] == "raised"
    assert retriever_module.MIN_SIMILARITY > original

    # restore
    retriever_module.MIN_SIMILARITY = original
    matcher_module.MIN_SIMILARITY = original


@pytest.mark.asyncio
async def test_match_feedback_no_feedback_returns_zero():
    from app.ml.meta_learner import process_match_feedback
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    db.execute = AsyncMock(return_value=mock_result)

    result = await process_match_feedback(db)
    assert result["processed"] == 0


# ─── process_score_feedback ─────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_score_feedback_extracts_corrections():
    from app.ml.meta_learner import process_score_feedback
    rows = [
        _make_feedback("negative", FeedbackTarget.lead_score, score_override=0.2),
        _make_feedback("positive", FeedbackTarget.lead_score, score_override=0.9),
        _make_feedback("neutral", FeedbackTarget.lead_score, score_override=None),
    ]

    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = rows
    db.execute = AsyncMock(return_value=mock_result)

    result = await process_score_feedback(db)
    assert result["processed"] == 3
    assert result["corrections"] == 2  # only rows with score_override != None


# ─── run_meta_learning_cycle ───────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_run_cycle_returns_ok_status():
    from app.ml.meta_learner import run_meta_learning_cycle

    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    db.execute = AsyncMock(return_value=mock_result)
    db.commit = AsyncMock()

    result = await run_meta_learning_cycle(db)
    assert result["status"] == "ok"
    assert "results" in result
    assert "elapsed_s" in result
    assert set(result["results"].keys()) == {
        "agent_response", "property_match", "lead_score", "rag_chunk"
    }
