"""
test_analytics.py — L2 unit tests for Node 5.2: analytics engine.
Tests: chart builders with sample data, edge cases (empty input), shape validation.
"""
import pytest
import pandas as pd

from app.analytics.reports import (
    funnel_chart,
    activity_chart,
    agent_performance_chart,
    property_distribution_charts,
    forecast_chart,
)


# ─── funnel_chart ───────────────────────────────────────────────────────────────
class TestFunnelChart:
    def _rows(self):
        return [
            {"stage": "nuevo", "count": 50},
            {"stage": "contactado", "count": 35},
            {"stage": "calificado", "count": 20},
            {"stage": "propuesta", "count": 10},
            {"stage": "negociacion", "count": 5},
            {"stage": "cerrado", "count": 3},
        ]

    def test_returns_dict_with_data_and_layout(self):
        chart = funnel_chart(self._rows())
        assert "data" in chart
        assert "layout" in chart

    def test_funnel_type(self):
        chart = funnel_chart(self._rows())
        assert chart["data"][0]["type"] == "funnel"

    def test_stage_count_in_x(self):
        chart = funnel_chart(self._rows())
        assert 50 in chart["data"][0]["x"]

    def test_empty_rows_returns_no_data(self):
        chart = funnel_chart([])
        assert chart["data"] == []

    def test_conversion_rates_in_meta(self):
        chart = funnel_chart(self._rows())
        assert "meta" in chart
        rates = chart["meta"]["conversion_rates"]
        assert "nuevo" in rates
        assert rates["nuevo"] == 100.0  # first stage is always 100%


# ─── activity_chart ────────────────────────────────────────────────────────────
class TestActivityChart:
    def _rows(self):
        return [
            {"day": "2026-06-01", "type": "call", "count": 5},
            {"day": "2026-06-01", "type": "whatsapp", "count": 12},
            {"day": "2026-06-02", "type": "call", "count": 3},
            {"day": "2026-06-02", "type": "visit", "count": 2},
        ]

    def test_returns_traces(self):
        chart = activity_chart(self._rows())
        assert len(chart["data"]) >= 1

    def test_scatter_type(self):
        chart = activity_chart(self._rows())
        assert all(t["type"] == "scatter" for t in chart["data"])

    def test_empty_returns_empty_data(self):
        chart = activity_chart([])
        assert chart["data"] == []

    def test_trace_names_are_interaction_types(self):
        chart = activity_chart(self._rows())
        names = {t["name"] for t in chart["data"]}
        assert "call" in names or "whatsapp" in names


# ─── agent_performance_chart ───────────────────────────────────────────────────
class TestAgentPerformanceChart:
    def _rows(self):
        return [
            {"agent_id": "1", "agent_name": "Ana", "interactions": 30,
             "visits": 5, "closed_deals": 3, "total_clients": 20, "conversion_rate": 0.15},
            {"agent_id": "2", "agent_name": "Luis", "interactions": 50,
             "visits": 10, "closed_deals": 8, "total_clients": 35, "conversion_rate": 0.23},
        ]

    def test_two_traces(self):
        chart = agent_performance_chart(self._rows())
        assert len(chart["data"]) == 2

    def test_bar_type(self):
        chart = agent_performance_chart(self._rows())
        assert all(t["type"] == "bar" for t in chart["data"])

    def test_conversion_rates_in_meta(self):
        chart = agent_performance_chart(self._rows())
        rates = chart["meta"]["conversion_rates"]
        assert "Ana" in rates
        assert rates["Luis"] == 0.23

    def test_empty(self):
        assert agent_performance_chart([]) == {
            "data": [], "layout": {"title": "Rendimiento agentes (sin datos)"}
        }


# ─── property_distribution_charts ──────────────────────────────────────────────
class TestPropertyDistributionCharts:
    def _dist(self):
        return {
            "by_type": [{"type": "departamento", "count": 80}, {"type": "casa", "count": 40}],
            "by_operation": [{"operation": "venta", "count": 90}, {"operation": "alquiler", "count": 30}],
            "by_neighborhood": [{"neighborhood": "Palermo", "count": 25}],
            "price_avg": [{"operation": "venta", "type": "departamento", "avg_price": 120000, "count": 80}],
        }

    def test_returns_four_chart_keys(self):
        charts = property_distribution_charts(self._dist())
        assert "by_type" in charts
        assert "by_operation" in charts
        assert "by_neighborhood" in charts
        assert "price_avg" in charts

    def test_by_type_is_pie(self):
        charts = property_distribution_charts(self._dist())
        assert charts["by_type"]["data"][0]["type"] == "pie"

    def test_empty_dist_returns_empty(self):
        charts = property_distribution_charts({})
        assert charts == {}


# ─── forecast_chart ─────────────────────────────────────────────────────────────
class TestForecastChart:
    def _rows(self):
        return [
            {"client_id": "1", "full_name": "Carlos", "lead_stage": "negociacion",
             "score": 0.82, "label": "hot"},
            {"client_id": "2", "full_name": "Maria", "lead_stage": "propuesta",
             "score": 0.61, "label": "warm"},
            {"client_id": "3", "full_name": "Jose", "lead_stage": "calificado",
             "score": 0.52, "label": "warm"},
        ]

    def test_returns_chart_with_data(self):
        chart = forecast_chart(self._rows())
        assert len(chart["data"]) == 1
        assert chart["data"][0]["type"] == "bar"

    def test_scores_in_x(self):
        chart = forecast_chart(self._rows())
        assert 0.82 in chart["data"][0]["x"]

    def test_names_in_y(self):
        chart = forecast_chart(self._rows())
        assert "Carlos" in chart["data"][0]["y"]

    def test_color_hot_is_red(self):
        chart = forecast_chart(self._rows())
        colors = chart["data"][0]["marker"]["color"]
        assert "#ef4444" in colors  # hot color

    def test_empty(self):
        chart = forecast_chart([])
        assert chart["data"] == []
