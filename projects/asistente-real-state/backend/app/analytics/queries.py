"""
queries.py — Raw data aggregations via SQLAlchemy.
Returns plain dicts/lists — no Pandas here, keeping DB layer pure.
"""
from datetime import datetime, timezone, timedelta
from sqlalchemy import func, select, case, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.client import Client, LeadStage
from app.models.interaction import Interaction, InteractionType
from app.models.property import Property
from app.models.event import Event
from app.models.user import User


async def funnel_counts(db: AsyncSession, agent_id: str | None = None) -> list[dict]:
    """Count clients per lead stage, optionally filtered by agent."""
    stmt = select(
        Client.lead_stage,
        func.count(Client.id).label("count"),
    ).group_by(Client.lead_stage)

    if agent_id:
        from uuid import UUID
        stmt = stmt.where(Client.agent_id == UUID(agent_id))

    rows = (await db.execute(stmt)).all()
    return [{"stage": r.lead_stage.value, "count": r.count} for r in rows]


async def interactions_over_time(
    db: AsyncSession,
    days: int = 30,
    agent_id: str | None = None,
) -> list[dict]:
    """Count interactions per day for the last N days."""
    since = datetime.now(timezone.utc) - timedelta(days=days)

    stmt = select(
        func.date_trunc("day", Interaction.created_at).label("day"),
        Interaction.interaction_type,
        func.count(Interaction.id).label("count"),
    ).where(Interaction.created_at >= since)

    if agent_id:
        from uuid import UUID
        stmt = stmt.where(Interaction.agent_id == UUID(agent_id))

    stmt = stmt.group_by("day", Interaction.interaction_type).order_by("day")
    rows = (await db.execute(stmt)).all()
    return [
        {
            "day": r.day.date().isoformat(),
            "type": r.interaction_type.value,
            "count": r.count,
        }
        for r in rows
    ]


async def agent_performance(db: AsyncSession, days: int = 30) -> list[dict]:
    """Per-agent: total interactions, visits, closed deals, conversion rate."""
    since = datetime.now(timezone.utc) - timedelta(days=days)

    inter_stmt = (
        select(
            Interaction.agent_id,
            func.count(Interaction.id).label("total"),
            func.sum(
                case((Interaction.interaction_type == InteractionType.visit, 1), else_=0)
            ).label("visits"),
        )
        .where(Interaction.created_at >= since)
        .group_by(Interaction.agent_id)
    )
    inter_rows = {str(r.agent_id): {"total": r.total, "visits": r.visits}
                  for r in (await db.execute(inter_stmt)).all()}

    closed_stmt = (
        select(Client.agent_id, func.count(Client.id).label("closed"))
        .where(
            Client.lead_stage == LeadStage.cerrado,
            Client.updated_at >= since,
        )
        .group_by(Client.agent_id)
    )
    closed_rows = {str(r.agent_id): r.closed
                   for r in (await db.execute(closed_stmt)).all()}

    total_stmt = (
        select(Client.agent_id, func.count(Client.id).label("total"))
        .group_by(Client.agent_id)
    )
    total_rows = {str(r.agent_id): r.total
                  for r in (await db.execute(total_stmt)).all()}

    agents = (await db.execute(select(User.id, User.full_name))).all()
    result = []
    for agent in agents:
        aid = str(agent.id)
        closed = closed_rows.get(aid, 0)
        total = total_rows.get(aid, 0)
        interactions = inter_rows.get(aid, {"total": 0, "visits": 0})
        conversion = round(closed / total, 4) if total > 0 else 0.0
        result.append({
            "agent_id": aid,
            "agent_name": agent.full_name,
            "interactions": interactions["total"],
            "visits": interactions["visits"],
            "closed_deals": closed,
            "total_clients": total,
            "conversion_rate": conversion,
        })
    return result


async def property_distribution(db: AsyncSession) -> dict:
    """Breakdown of properties by type, operation, and neighborhood."""
    by_type = (
        select(Property.property_type, func.count(Property.id).label("count"))
        .group_by(Property.property_type)
    )
    by_op = (
        select(Property.operation_type, func.count(Property.id).label("count"))
        .group_by(Property.operation_type)
    )
    by_hood = (
        select(Property.neighborhood, func.count(Property.id).label("count"))
        .where(Property.neighborhood.is_not(None))
        .group_by(Property.neighborhood)
        .order_by(text("count DESC"))
        .limit(15)
    )
    price_avg = (
        select(
            Property.operation_type,
            Property.property_type,
            func.avg(Property.price).label("avg_price"),
            func.count(Property.id).label("count"),
        )
        .where(Property.price.is_not(None))
        .group_by(Property.operation_type, Property.property_type)
    )

    return {
        "by_type": [{"type": r.property_type, "count": r.count}
                    for r in (await db.execute(by_type)).all()],
        "by_operation": [{"operation": r.operation_type, "count": r.count}
                         for r in (await db.execute(by_op)).all()],
        "by_neighborhood": [{"neighborhood": r.neighborhood, "count": r.count}
                            for r in (await db.execute(by_hood)).all()],
        "price_avg": [
            {"operation": r.operation_type, "type": r.property_type,
             "avg_price": round(float(r.avg_price), 0), "count": r.count}
            for r in (await db.execute(price_avg)).all()
        ],
    }


async def closing_forecast(
    db: AsyncSession,
    horizon_days: int = 30,
    min_score: float = 0.50,
) -> list[dict]:
    """
    Return clients with high closing probability (scored in real-time).
    Uses the ML predictor — no extra DB query needed beyond client+interactions.
    """
    from sqlalchemy.orm import selectinload
    from app.models.interaction import Interaction
    from app.ml.features import extract_features
    from app.ml.predictor import score_lead
    from app.models.client import LeadStage

    active_stages = [
        LeadStage.contactado, LeadStage.calificado,
        LeadStage.propuesta, LeadStage.negociacion,
    ]
    clients = (
        await db.execute(
            select(Client).where(Client.lead_stage.in_(active_stages)).limit(500)
        )
    ).scalars().all()

    results = []
    for client in clients:
        interactions = (
            await db.execute(
                select(Interaction).where(Interaction.client_id == client.id)
            )
        ).scalars().all()
        events = (
            await db.execute(
                select(Event).where(Event.client_id == client.id)
            )
        ).scalars().all()

        feats = extract_features(client, interactions, events)
        score_result = score_lead(feats)

        if score_result.score >= min_score:
            results.append({
                "client_id": str(client.id),
                "full_name": client.full_name,
                "lead_stage": client.lead_stage.value,
                "score": score_result.score,
                "label": score_result.label,
            })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results
