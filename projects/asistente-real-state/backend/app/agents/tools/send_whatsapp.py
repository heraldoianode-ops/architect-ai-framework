"""
send_whatsapp tool — sends a WhatsApp message via the Node.js gateway.
The agent calls this to proactively notify clients or agents.
"""
from langchain_core.tools import tool
import httpx
from app.core.config import get_settings

settings = get_settings()

GATEWAY_URL = "http://gateway:3000"


@tool
async def send_whatsapp_message(to: str, message: str) -> str:
    """
    Send a WhatsApp message to a contact via the gateway.
    Use for proactive notifications: new property match, appointment confirmation,
    or escalation to human agent.

    Args:
        to: recipient WhatsApp ID (phone with country code, e.g. '5491112345678')
        message: text message to send (max 4096 chars)
    """
    if len(message) > 4096:
        message = message[:4090] + "..."

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{GATEWAY_URL}/send",
                json={"to": to, "text": message},
            )
            resp.raise_for_status()
        return f"Mensaje enviado a {to}."
    except httpx.HTTPStatusError as e:
        return f"Error al enviar mensaje: HTTP {e.response.status_code}"
    except Exception as e:
        return f"Error al enviar mensaje: {e}"


@tool
async def escalate_to_human(wa_contact_id: str, reason: str) -> str:
    """
    Flag a WhatsApp conversation for human agent takeover.
    Use when the AI cannot resolve the query, client is upset, or asks to speak to a person.

    Args:
        wa_contact_id: WhatsApp contact ID of the client
        reason: brief reason for escalation
    """
    from app.core.redis import get_redis
    r = await get_redis()
    await r.setex(f"escalate:{wa_contact_id}", 86400, reason)

    # Notify all online agents via gateway broadcast endpoint
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            await client.post(
                f"{GATEWAY_URL}/send",
                json={
                    "to": "AGENT_BROADCAST",  # gateway handles routing to online agents
                    "text": f"🔔 Cliente {wa_contact_id} requiere atención humana.\nMotivo: {reason}",
                },
            )
    except Exception:
        pass  # notification is best-effort

    return f"Conversación de {wa_contact_id} escalada a agente humano. Motivo: {reason}"
