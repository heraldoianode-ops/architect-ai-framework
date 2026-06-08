"""
schedule_event tool — creates a calendar event (visit, capture, meeting).
The agent calls this when a client confirms an appointment via WhatsApp.
"""
from langchain_core.tools import tool
from datetime import datetime
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.client import Client
from app.models.event import Event, EventType


@tool
async def schedule_event(
    wa_contact_id: str,
    event_type: str,
    scheduled_at_iso: str,
    title: str,
    location: str = "",
    duration_min: int = 60,
) -> str:
    """
    Schedule a calendar event for a client.
    Use when the client confirms they want to visit a property, meet an agent,
    or when a seller wants to schedule a property capture appointment.

    Args:
        wa_contact_id: WhatsApp contact ID of the client
        event_type: one of 'visita_comprador', 'captacion_vendedor', 'reunion_agente', 'llamada'
        scheduled_at_iso: ISO datetime string e.g. '2026-06-15T10:00:00'
        title: short description e.g. 'Visita depto Palermo - Av. Santa Fe 1234'
        location: address or meeting link
        duration_min: duration in minutes (default 60)
    """
    try:
        scheduled_at = datetime.fromisoformat(scheduled_at_iso)
    except ValueError:
        return f"Fecha inválida: '{scheduled_at_iso}'. Usá formato ISO: 'YYYY-MM-DDTHH:MM:SS'."

    try:
        ev_type = EventType(event_type)
    except ValueError:
        valid = [e.value for e in EventType]
        return f"Tipo de evento inválido: '{event_type}'. Opciones: {valid}"

    async with AsyncSessionLocal() as db:
        client_result = await db.execute(
            select(Client).where(Client.whatsapp_id == wa_contact_id)
        )
        client = client_result.scalar_one_or_none()
        if not client:
            return f"No encontré cliente con WhatsApp ID '{wa_contact_id}'. Registralo primero."

        event = Event(
            client_id=client.id,
            agent_id=client.agent_id,
            event_type=ev_type,
            title=title,
            location=location or None,
            scheduled_at=scheduled_at,
            duration_min=duration_min,
        )
        db.add(event)
        await db.commit()

    fecha = scheduled_at.strftime("%d/%m/%Y a las %H:%M")
    return (
        f"Evento agendado correctamente.\n"
        f"Tipo: {ev_type.value}\n"
        f"Fecha: {fecha}\n"
        f"Título: {title}\n"
        f"Lugar: {location or 'Por confirmar'}\n"
        f"Se enviará recordatorio 24h y 1h antes por WhatsApp."
    )
