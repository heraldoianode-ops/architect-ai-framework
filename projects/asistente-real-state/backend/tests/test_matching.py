"""
test_matching.py — L2 unit tests for Node 4.2: semantic matching engine.
Tests: build_property_text, build_preference_text, filter logic, embedder wiring.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass

from app.matching.property_matcher import build_property_text, MIN_SIMILARITY, PropertyMatch
from app.matching.preference_embedder import build_preference_text


# ─── build_property_text ────────────────────────────────────────────────────────
class TestBuildPropertyText:
    def _prop(self, **kwargs):
        p = MagicMock()
        p.operation_type = kwargs.get("operation_type", "venta")
        p.property_type = kwargs.get("property_type", "departamento")
        p.neighborhood = kwargs.get("neighborhood", "Palermo")
        p.city = kwargs.get("city", "Buenos Aires")
        p.price = kwargs.get("price", 120000.0)
        p.currency = kwargs.get("currency", "USD")
        p.rooms = kwargs.get("rooms", 3)
        p.sqm_total = kwargs.get("sqm_total", 75.0)
        p.title = kwargs.get("title", "Dpto luminoso")
        p.description = kwargs.get("description", "")
        return p

    def test_includes_operation_and_type(self):
        text = build_property_text(self._prop())
        assert "venta" in text
        assert "departamento" in text

    def test_includes_neighborhood(self):
        text = build_property_text(self._prop(neighborhood="Belgrano"))
        assert "Belgrano" in text

    def test_includes_price(self):
        text = build_property_text(self._prop(price=85000.0, currency="USD"))
        assert "85" in text  # formatted number
        assert "USD" in text

    def test_includes_rooms(self):
        text = build_property_text(self._prop(rooms=4))
        assert "4" in text
        assert "ambientes" in text

    def test_no_neighborhood_omitted(self):
        text = build_property_text(self._prop(neighborhood=None))
        assert "en" not in text

    def test_no_price_omitted(self):
        text = build_property_text(self._prop(price=None))
        assert "USD" not in text

    def test_returns_nonempty_string(self):
        text = build_property_text(self._prop())
        assert len(text) > 10


# ─── build_preference_text ────────────────────────────────────────────────────
class TestBuildPreferenceText:
    def test_full_preferences(self):
        prefs = {
            "operation_type": "alquiler",
            "property_type": "departamento",
            "neighborhood": "Palermo",
            "max_price": 1200,
            "currency": "USD",
            "min_rooms": 2,
            "notes": "cerca del subte",
        }
        text = build_preference_text(prefs)
        assert "alquiler" in text
        assert "departamento" in text
        assert "Palermo" in text
        assert "1,200" in text or "1200" in text
        assert "2 ambientes" in text
        assert "cerca del subte" in text

    def test_partial_preferences(self):
        prefs = {"operation_type": "venta", "city": "Córdoba"}
        text = build_preference_text(prefs)
        assert "venta" in text
        assert "Córdoba" in text

    def test_empty_preferences_return_empty(self):
        assert build_preference_text({}) == ""

    def test_notes_only(self):
        text = build_preference_text({"notes": "quiero algo con terraza"})
        assert "terraza" in text

    def test_type_only(self):
        text = build_preference_text({"property_type": "casa"})
        assert "casa" in text


# ─── MIN_SIMILARITY ──────────────────────────────────────────────────────────────
def test_min_similarity_threshold():
    assert 0.0 < MIN_SIMILARITY < 1.0


# ─── update_client_preference_embedding ──────────────────────────────────────
@pytest.mark.asyncio
async def test_update_preference_embedding_returns_false_if_empty_prefs():
    from app.matching.preference_embedder import update_client_preference_embedding
    db = AsyncMock()
    result = await update_client_preference_embedding("00000000-0000-0000-0000-000000000001", {}, db)
    assert result is False


@pytest.mark.asyncio
async def test_update_preference_embedding_returns_false_if_client_not_found():
    from app.matching.preference_embedder import update_client_preference_embedding
    from app.models.client import Client

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None

    db = AsyncMock()
    db.execute = AsyncMock(return_value=mock_result)

    prefs = {"operation_type": "alquiler", "neighborhood": "Palermo"}
    with patch("app.matching.preference_embedder.embed_text", AsyncMock(return_value=[0.1] * 768)):
        result = await update_client_preference_embedding(
            "00000000-0000-0000-0000-000000000001", prefs, db
        )
    assert result is False


@pytest.mark.asyncio
async def test_update_preference_embedding_stores_vector():
    from app.matching.preference_embedder import update_client_preference_embedding
    from app.models.client import Client

    fake_client = MagicMock(spec=Client)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = fake_client

    db = AsyncMock()
    db.execute = AsyncMock(return_value=mock_result)
    db.commit = AsyncMock()

    fake_vector = [0.5] * 768
    prefs = {"operation_type": "venta", "property_type": "casa", "neighborhood": "San Telmo"}

    with patch("app.matching.preference_embedder.embed_text", AsyncMock(return_value=fake_vector)):
        result = await update_client_preference_embedding(
            "00000000-0000-0000-0000-000000000001", prefs, db
        )

    assert result is True
    assert fake_client.preference_embedding == fake_vector
    db.commit.assert_awaited_once()


# ─── match_for_client — no embedding path ─────────────────────────────────────
@pytest.mark.asyncio
async def test_match_for_client_no_embedding_returns_empty():
    from app.matching.property_matcher import match_for_client
    from app.models.client import Client

    fake_client = MagicMock(spec=Client)
    fake_client.preference_embedding = None

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = fake_client

    db = AsyncMock()
    db.execute = AsyncMock(return_value=mock_result)

    result = await match_for_client("00000000-0000-0000-0000-000000000001", db)
    assert result == []
