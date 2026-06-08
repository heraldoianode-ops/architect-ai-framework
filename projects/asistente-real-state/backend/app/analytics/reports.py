"""
reports.py — Pandas transformations + Plotly chart generation.
All charts returned as JSON-serializable dicts (Plotly figure format)
for rendering with Plotly.js on the frontend — no server-side image rendering.
"""
from __future__ import annotations
import pandas as pd
from typing import Any

# ─── Funnel ───────────────────────────────────────────────────────────────────
_STAGE_ORDER = [
    "nuevo", "contactado", "calificado",
    "propuesta", "negociacion", "cerrado", "perdido",
]


def funnel_chart(funnel_rows: list[dict]) -> dict:
    """
    Build a Plotly funnel chart from stage count data.
    Returns Plotly figure dict.
    """
    df = pd.DataFrame(funnel_rows)
    if df.empty:
        return {"data": [], "layout": {"title": "Funnel (sin datos)"}}

    df["stage"] = pd.Categorical(df["stage"], categories=_STAGE_ORDER, ordered=True)
    df = df.sort_values("stage")

    # Conversion rates between consecutive stages
    df = df.reset_index(drop=True)
    totals = df["count"].tolist()
    stages = df["stage"].tolist()

    conversions = []
    for i in range(len(totals)):
        prev = totals[i - 1] if i > 0 else totals[0]
        pct = round(totals[i] / prev * 100, 1) if prev > 0 else 0.0
        conversions.append(pct)

    return {
        "data": [{
            "type": "funnel",
            "y": stages,
            "x": totals,
            "textinfo": "value+percent previous",
            "marker": {"color": [
                "#6366f1", "#8b5cf6", "#a78bfa",
                "#c4b5fd", "#ddd6fe", "#22c55e", "#ef4444",
            ][:len(stages)]},
        }],
        "layout": {
            "title": "Funnel de leads",
            "margin": {"l": 120},
        },
        "meta": {"conversion_rates": dict(zip(stages, conversions))},
    }


# ─── Activity timeline ────────────────────────────────────────────────────────
def activity_chart(interaction_rows: list[dict]) -> dict:
    """
    Multi-line chart: interactions per day broken down by type.
    """
    if not interaction_rows:
        return {"data": [], "layout": {"title": "Actividad (sin datos)"}}

    df = pd.DataFrame(interaction_rows)
    df["day"] = pd.to_datetime(df["day"])
    pivot = df.pivot_table(index="day", columns="type", values="count", aggfunc="sum", fill_value=0)
    pivot = pivot.reset_index()

    color_map = {
        "note": "#94a3b8", "call": "#3b82f6", "whatsapp": "#22c55e",
        "email": "#f59e0b", "visit": "#8b5cf6", "meeting": "#ef4444",
    }

    traces = []
    for col in pivot.columns:
        if col == "day":
            continue
        traces.append({
            "type": "scatter",
            "mode": "lines+markers",
            "name": col,
            "x": pivot["day"].dt.strftime("%Y-%m-%d").tolist(),
            "y": pivot[col].tolist(),
            "line": {"color": color_map.get(col, "#64748b")},
        })

    return {
        "data": traces,
        "layout": {
            "title": "Actividad diaria por tipo",
            "xaxis": {"title": "Fecha"},
            "yaxis": {"title": "Interacciones"},
            "legend": {"orientation": "h"},
        },
    }


# ─── Agent performance ────────────────────────────────────────────────────────
def agent_performance_chart(rows: list[dict]) -> dict:
    """Grouped bar chart: interactions + closed deals per agent."""
    if not rows:
        return {"data": [], "layout": {"title": "Rendimiento agentes (sin datos)"}}

    df = pd.DataFrame(rows).sort_values("closed_deals", ascending=False)
    names = df["agent_name"].tolist()

    return {
        "data": [
            {
                "type": "bar",
                "name": "Interacciones",
                "x": names,
                "y": df["interactions"].tolist(),
                "marker": {"color": "#6366f1"},
            },
            {
                "type": "bar",
                "name": "Cierres",
                "x": names,
                "y": df["closed_deals"].tolist(),
                "marker": {"color": "#22c55e"},
            },
        ],
        "layout": {
            "title": "Rendimiento por agente",
            "barmode": "group",
            "xaxis": {"title": "Agente"},
            "yaxis": {"title": "Cantidad"},
        },
        "meta": {
            "conversion_rates": {
                row["agent_name"]: row["conversion_rate"] for row in rows
            }
        },
    }


# ─── Property distribution ────────────────────────────────────────────────────
def property_distribution_charts(dist: dict) -> dict:
    """Returns multiple Plotly charts for the property report."""
    charts: dict[str, Any] = {}

    # By type — pie
    if dist.get("by_type"):
        df = pd.DataFrame(dist["by_type"])
        charts["by_type"] = {
            "data": [{"type": "pie", "labels": df["type"].tolist(),
                      "values": df["count"].tolist(), "hole": 0.4}],
            "layout": {"title": "Propiedades por tipo"},
        }

    # By operation — pie
    if dist.get("by_operation"):
        df = pd.DataFrame(dist["by_operation"])
        charts["by_operation"] = {
            "data": [{"type": "pie", "labels": df["operation"].tolist(),
                      "values": df["count"].tolist()}],
            "layout": {"title": "Por tipo de operación"},
        }

    # By neighborhood — horizontal bar
    if dist.get("by_neighborhood"):
        df = pd.DataFrame(dist["by_neighborhood"]).head(10)
        charts["by_neighborhood"] = {
            "data": [{
                "type": "bar",
                "orientation": "h",
                "x": df["count"].tolist(),
                "y": df["neighborhood"].tolist(),
                "marker": {"color": "#8b5cf6"},
            }],
            "layout": {
                "title": "Top 10 barrios",
                "xaxis": {"title": "Propiedades"},
                "margin": {"l": 140},
            },
        }

    # Price avg — scatter
    if dist.get("price_avg"):
        df = pd.DataFrame(dist["price_avg"])
        df["label"] = df["operation"] + " / " + df["type"]
        charts["price_avg"] = {
            "data": [{
                "type": "bar",
                "x": df["label"].tolist(),
                "y": df["avg_price"].tolist(),
                "text": [f"n={r}" for r in df["count"].tolist()],
                "textposition": "outside",
                "marker": {"color": "#f59e0b"},
            }],
            "layout": {
                "title": "Precio promedio por tipo y operación",
                "xaxis": {"tickangle": -30},
                "yaxis": {"title": "USD"},
            },
        }

    return charts


# ─── Closing forecast ─────────────────────────────────────────────────────────
def forecast_chart(forecast_rows: list[dict]) -> dict:
    """Horizontal bar chart: top prospects ranked by closing probability."""
    if not forecast_rows:
        return {"data": [], "layout": {"title": "Forecast de cierres (sin datos)"}}

    df = pd.DataFrame(forecast_rows).head(20)
    color_map = {"hot": "#ef4444", "warm": "#f59e0b", "cold": "#94a3b8"}

    return {
        "data": [{
            "type": "bar",
            "orientation": "h",
            "x": df["score"].tolist(),
            "y": df["full_name"].tolist(),
            "text": [f"{s:.0%}" for s in df["score"].tolist()],
            "textposition": "outside",
            "marker": {
                "color": [color_map.get(l, "#94a3b8") for l in df["label"].tolist()]
            },
        }],
        "layout": {
            "title": "Clientes con mayor probabilidad de cierre",
            "xaxis": {"range": [0, 1.05], "tickformat": ".0%"},
            "margin": {"l": 180},
        },
    }
