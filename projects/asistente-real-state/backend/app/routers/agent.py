"""
/agent router — entry point for the WhatsApp gateway and direct API calls.
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
import structlog

from app.agents.react_agent import run_whatsapp_agent
from app.core.redis import get_redis

router = APIRouter(prefix="/agent", tags=["agent"])
log = structlog.get_logger()


class WhatsAppInbound(BaseModel):
    wa_contact_id: str
    message: str
    message_id: str | None = None
    timestamp: str | None = None


class AgentResponse(BaseModel):
    reply: str
    escalated: bool = False


@router.post("/whatsapp", response_model=AgentResponse)
async def whatsapp_agent(body: WhatsAppInbound):
    """
    Called by the Node.js gateway for every inbound WhatsApp message.
    Returns the agent's reply text for the gateway to send back.
    """
    # Check if conversation is escalated to human agent
    r = await get_redis()
    is_escalated = await r.exists(f"escalate:{body.wa_contact_id}")
    if is_escalated:
        log.info("agent.escalated_skip", wa_id=body.wa_contact_id)
        return AgentResponse(
            reply="",  # gateway will suppress bot reply when escalated
            escalated=True,
        )

    try:
        reply = await run_whatsapp_agent(body.wa_contact_id, body.message)
        # Re-check if agent escalated during this run
        is_escalated = await r.exists(f"escalate:{body.wa_contact_id}")
        return AgentResponse(reply=reply, escalated=bool(is_escalated))
    except Exception as e:
        log.error("agent.endpoint_error", error=str(e))
        raise HTTPException(status_code=500, detail="Error procesando mensaje")


class DirectQuery(BaseModel):
    message: str
    session_id: str = "direct_query"
    agent_name: str | None = None


@router.post("/query")
async def direct_query(body: DirectQuery):
    """
    Direct agent query for internal use (dashboard, admin testing, analytics generation).
    Supports agent_name to route to authorized external LLM agents.
    """
    reply = await run_whatsapp_agent(body.session_id, body.message)
    return {"reply": reply}


@router.delete("/session/{wa_contact_id}")
async def clear_session(wa_contact_id: str):
    """Clear conversation memory and escalation flag for a WhatsApp contact."""
    r = await get_redis()
    await r.delete(f"session:{wa_contact_id}")
    await r.delete(f"escalate:{wa_contact_id}")
    return {"cleared": wa_contact_id}
