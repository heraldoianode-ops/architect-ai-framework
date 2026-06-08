"""
Level 2 tests for the ReAct agent — mock Ollama and DB.
Tests: tool registration, session memory, escalation flag, ai_policy enforcement.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.agents.react_agent import build_agent, run_whatsapp_agent, _format_history
from app.core.config import get_settings


# ─── ai_policy enforcement ────────────────────────────────────────────────────

def test_default_llm_is_local():
    """System must use local Ollama by default — zero token cost."""
    settings = get_settings()
    assert settings.allow_external_llm is False
    mode, model = settings.get_llm(agent_name=None)
    assert mode == "local"
    assert "llama" in model.lower() or "mistral" in model.lower()


def test_external_llm_blocked_without_flag():
    """External LLM must not be used even for authorized agents if flag is False."""
    settings = get_settings()
    # Simulate authorized agent but flag is off
    with patch.object(settings, "allow_external_llm", False):
        mode, _ = settings.get_llm("rag_legal_agent")
        assert mode == "local"


def test_external_llm_allowed_only_for_authorized_agent():
    """External LLM must only activate for authorized agent names when flag is True."""
    settings = get_settings()
    with patch.object(settings, "allow_external_llm", True), \
         patch.object(settings, "anthropic_api_key", "sk-test-key"):
        # Authorized agent
        mode, _ = settings.get_llm("rag_legal_agent")
        assert mode == "external"
        # Unauthorized agent
        mode2, _ = settings.get_llm("some_random_agent")
        assert mode2 == "local"


# ─── Tool registration ────────────────────────────────────────────────────────

def test_agent_has_required_tools():
    """Agent must have all 5 base tools registered."""
    from app.agents.react_agent import BASE_TOOLS
    tool_names = {t.name for t in BASE_TOOLS}
    required = {
        "search_properties",
        "get_client_history",
        "schedule_event",
        "send_whatsapp_message",
        "escalate_to_human",
    }
    assert required.issubset(tool_names), f"Missing tools: {required - tool_names}"


# ─── Session memory ───────────────────────────────────────────────────────────

def test_format_history_empty():
    assert "Sin historial" in _format_history([])


def test_format_history_truncates_to_6():
    session = [{"role": "user", "content": f"msg {i}"} for i in range(20)]
    result = _format_history(session)
    # Should only include last 6 messages
    assert "msg 19" in result
    assert "msg 0" not in result


# ─── Escalation flag ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_escalated_conversation_skips_agent():
    """When escalate flag is set in Redis, agent endpoint must return escalated=True with empty reply."""
    from fastapi.testclient import TestClient
    from app.main import app

    mock_redis = AsyncMock()
    mock_redis.exists = AsyncMock(return_value=1)  # escalation flag set

    with patch("app.routers.agent.get_redis", return_value=mock_redis):
        client = TestClient(app)
        resp = client.post("/agent/whatsapp", json={
            "wa_contact_id": "5491112345678",
            "message": "Hola, qué tienen disponible?",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["escalated"] is True
        assert data["reply"] == ""
