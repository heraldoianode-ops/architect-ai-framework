"""
analytics.py — Analytics dashboard endpoints.
All responses include both raw data and a Plotly chart spec.
"""
from typing import Any
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_agent_or_above
from app.core.database import get_db
from app.analytics import queries
from app.analytics.reports import (
    funnel_chart,
    activity_chart,
    agent_performance_chart,
    property_distribution_charts,
    forecast_chart,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])


class ChartResponse(BaseModel):
    data: list[dict]
    chart: dict


# ─── Funnel ────────────────────────────────────────────────────────────────────
@router.get("/funnel")
async def get_funnel(
    agent_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _: Any = Depends(require_agent_or_above),
) -> dict:
    rows = await queries.funnel_counts(db, agent_id)
    return {"data": rows, "chart": funnel_chart(rows)}


# ─── Activity ──────────────────────────────────────────────────────────────────
@router.get("/activity")
async def get_activity(
    days: int = Query(30, ge=7, le=365),
    agent_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _: Any = Depends(require_agent_or_above),
) -> dict:
    rows = await queries.interactions_over_time(db, days=days, agent_id=agent_id)
    return {"data": rows, "chart": activity_chart(rows)}


# ─── Agent performance ─────────────────────────────────────────────────────────
@router.get("/agents")
async def get_agent_performance(
    days: int = Query(30, ge=7, le=365),
    db: AsyncSession = Depends(get_db),
    _: Any = Depends(require_agent_or_above),
) -> dict:
    rows = await queries.agent_performance(db, days=days)
    return {"data": rows, "chart": agent_performance_chart(rows)}


# ─── Property distribution ───────────────────────────────────────────────────────
@router.get("/properties")
async def get_property_distribution(
    db: AsyncSession = Depends(get_db),
    _: Any = Depends(require_agent_or_above),
) -> dict:
    dist = await queries.property_distribution(db)
    charts = property_distribution_charts(dist)
    return {"data": dist, "charts": charts}


# ─── Closing forecast ─────────────────────────────────────────────────────────
@router.get("/forecast")
async def get_forecast(
    min_score: float = Query(0.50, ge=0.1, le=0.99),
    db: AsyncSession = Depends(get_db),
    _: Any = Depends(require_agent_or_above),
) -> dict:
    rows = await queries.closing_forecast(db, min_score=min_score)
    return {"data": rows, "chart": forecast_chart(rows)}


# ─── Summary (all KPIs in one call for the dashboard home) ──────────────────
@router.get("/summary")
async def get_summary(
    db: AsyncSession = Depends(get_db),
    _: Any = Depends(require_agent_or_above),
) -> dict:
    """Single endpoint returning key KPIs for the dashboard home card."""
    from sqlalchemy import func, select
    from app.models.client import Client, LeadStage
    from app.models.property import Property
    from app.models.interaction import Interaction
    from datetime import datetime, timezone, timedelta

    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)

    total_clients = (await db.execute(select(func.count(Client.id)))).scalar_one()
    hot_leads = (await db.execute(
        select(func.count(Client.id)).where(
            Client.lead_stage.in_([LeadStage.propuesta, LeadStage.negociacion])
        )
    )).scalar_one()
    total_properties = (await db.execute(select(func.count(Property.id)))).scalar_one()
    interactions_week = (await db.execute(
        select(func.count(Interaction.id)).where(Interaction.created_at >= week_ago)
    )).scalar_one()
    closed_month = (await db.execute(
        select(func.count(Client.id)).where(
            Client.lead_stage == LeadStage.cerrado,
            Client.updated_at >= now - timedelta(days=30),
        )
    )).scalar_one()

    return {
        "total_clients": total_clients,
        "hot_leads": hot_leads,
        "total_properties": total_properties,
        "interactions_this_week": interactions_week,
        "closed_this_month": closed_month,
    }
