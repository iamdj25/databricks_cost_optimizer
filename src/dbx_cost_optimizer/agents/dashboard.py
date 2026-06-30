"""Dashboard Agent — creates a Databricks AI/BI (Lakeview) dashboard.

Builds a serialized dashboard over the findings + usage tables written by the
Sink agent: KPI counters, savings-by-fix-family bar, daily spend trend, and a
ranked findings table. Needs a live workspace (SDK) + SQL warehouse.
"""
from __future__ import annotations

import json
from typing import List, Optional

from ..models import Finding
from ..registry import register_agent
from ..workspace import get_workspace_client, resolve_warehouse_id
from .base import BaseAgent


def _build_serialized_dashboard(findings_tbl: str, usage_tbl: str) -> dict:
    return {
        "datasets": [
            {"name": "findings", "displayName": "Findings",
             "queryLines": [f"SELECT * FROM {findings_tbl}"]},
            {"name": "by_family", "displayName": "Savings by fix family",
             "queryLines": [
                 f"SELECT fix_family, SUM(monthly_savings_usd) AS savings, COUNT(*) AS n "
                 f"FROM {findings_tbl} GROUP BY fix_family ORDER BY savings DESC"]},
            {"name": "usage", "displayName": "Daily spend",
             "queryLines": [f"SELECT usage_date, cost_usd FROM {usage_tbl} ORDER BY usage_date"]},
        ],
        "pages": [{
            "name": "overview",
            "displayName": "Cost Optimization",
            "layout": [
                {"position": {"x": 0, "y": 0, "width": 2, "height": 3},
                 "widget": {"name": "kpi_savings", "queries": [{"name": "main", "query": {
                     "datasetName": "findings", "fields": [
                         {"name": "total", "expression": "SUM(`monthly_savings_usd`)"}],
                     "disaggregated": False}}],
                     "spec": {"version": 2, "widgetType": "counter",
                              "encodings": {"value": {"fieldName": "total", "displayName": "Monthly savings $"}}}}},
                {"position": {"x": 2, "y": 0, "width": 4, "height": 3},
                 "widget": {"name": "kpi_count", "queries": [{"name": "main", "query": {
                     "datasetName": "findings", "fields": [
                         {"name": "n", "expression": "COUNT(`id`)"}], "disaggregated": False}}],
                     "spec": {"version": 2, "widgetType": "counter",
                              "encodings": {"value": {"fieldName": "n", "displayName": "Findings"}}}}},
                {"position": {"x": 0, "y": 3, "width": 3, "height": 6},
                 "widget": {"name": "bar_family", "queries": [{"name": "main", "query": {
                     "datasetName": "by_family", "fields": [
                         {"name": "fix_family", "expression": "`fix_family`"},
                         {"name": "savings", "expression": "`savings`"}], "disaggregated": True}}],
                     "spec": {"version": 3, "widgetType": "bar",
                              "encodings": {"x": {"fieldName": "fix_family", "scale": {"type": "categorical"}},
                                            "y": {"fieldName": "savings", "scale": {"type": "quantitative"}}}}}},
                {"position": {"x": 3, "y": 3, "width": 3, "height": 6},
                 "widget": {"name": "trend", "queries": [{"name": "main", "query": {
                     "datasetName": "usage", "fields": [
                         {"name": "usage_date", "expression": "`usage_date`"},
                         {"name": "cost_usd", "expression": "`cost_usd`"}], "disaggregated": True}}],
                     "spec": {"version": 3, "widgetType": "line",
                              "encodings": {"x": {"fieldName": "usage_date", "scale": {"type": "categorical"}},
                                            "y": {"fieldName": "cost_usd", "scale": {"type": "quantitative"}}}}}},
                {"position": {"x": 0, "y": 9, "width": 6, "height": 8},
                 "widget": {"name": "table", "queries": [{"name": "main", "query": {
                     "datasetName": "findings",
                     "fields": [{"name": c, "expression": f"`{c}`"} for c in
                                ["recommendation", "fix_family", "monthly_savings_usd",
                                 "effort", "risk", "doc_url"]], "disaggregated": True}}],
                     "spec": {"version": 1, "widgetType": "table"}}},
            ],
        }],
    }


@register_agent
class DashboardAgent(BaseAgent):
    name = "dashboard"
    requires: List[str] = []
    tier = 4

    def __init__(self, settings, connector) -> None:
        super().__init__(settings, connector)
        self._w = None

    @property
    def w(self):
        if self._w is None:
            self._w = get_workspace_client(self.settings)
        return self._w

    def run(self, ctx) -> List[Finding]:
        db = self.settings.databricks
        wh = resolve_warehouse_id(self.settings, self.w)
        if not wh:
            ctx.meta["dashboard_error"] = "no warehouse_id (set DBX_WAREHOUSE_ID)"
            return []

        spec = _build_serialized_dashboard(db.findings_table, db.usage_table)
        try:
            from databricks.sdk.service.dashboards import Dashboard

            created = self.w.lakeview.create(dashboard=Dashboard(
                display_name="Databricks Cost Optimizer",
                warehouse_id=wh,
                serialized_dashboard=json.dumps(spec),
            ))
            did = getattr(created, "dashboard_id", None)
            try:
                self.w.lakeview.publish(dashboard_id=did, warehouse_id=wh)
            except Exception as pe:
                ctx.meta["dashboard_publish_warning"] = str(pe)
            ctx.meta["dashboard_id"] = did
            ctx.meta["dashboard_url"] = f"https://{db.server_hostname}/dashboardsv3/{did}"
        except Exception as e:
            ctx.meta["dashboard_error"] = str(e)
        return []

    def create(self, ctx) -> Optional[str]:
        self.run(ctx)
        return ctx.meta.get("dashboard_id")
