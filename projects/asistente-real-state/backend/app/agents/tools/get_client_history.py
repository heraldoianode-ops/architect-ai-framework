"""
get_client_history tool — retrieves a client's full CRM history.
The agent calls this before responding so it has full context about the person.
"""
from langchain_core.tools import tool
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.client import Client
from app.models.event import Event
from app.core.redis import get_session


@tool
async def get_client_history(wa_contact_id: str) -> str:
    """
    Retrieve the full history of a client by their WhatsApp contact ID.
    Use this FIRST when a message arrives to understand who the client is,
    their interests, lead stage, and past interactions.

    Args:
        wa_contact_id: WhatsApp contact ID (phone number with country code, e.g. '5491112345678')
    """
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Client).where(Client.whatsapp_id == wa_contact_id)
        )
        client = result.scalar_one_or_none()

        if not client:
            return (
                f"Cliente nuevo (ID WhatsApp: {wa_contact_id}). "
                "No hay historial previo. Presentate y preguntá qué está buscando."
            )

        # Recent events
        ev_result = await db.execute(
            select(Event)
            .where(Event.client_id == client.id)
            .order_by(Event.scheduled_at.desc())
            .limit(5)
        )
        events = ev_result.scalars().all()

    # Conversation window from Redis
    session = await get_session(wa_contact_id)

    lines = [
        f"Cliente: {client.full_name}",
        f"Etapa pipeline: {client.stage.value}",
        f"Score: {client.score}/100",
        f"Probabilidad de cierre: {client.closing_prob or 'N/D'}%",
        f"Zonas buscadas: {', '.join(client.search_zones or []) or 'No especificadas'}",
        f"Presupuesto: USD {client.budget_min or 0:,.0f} – {client.budget_max or 0:,.0f}",
        f"Tags: {', '.join(client.tags or [])}",
        f"Notas: {client.notes or 'Ninguna'}",
    ]

    if events:
        lines.append("\nÚltimos eventos:")
        for e in events:
            lines.append(f"  • {e.event_type.value} — {e.scheduled_at.strftime('%d/%m/%Y %H:%M')} — {e.status.value}")

    if session:
        lines.append(f"\nMensajes recientes en sesión: {len(session)}")

    return "\n".join(lines)
