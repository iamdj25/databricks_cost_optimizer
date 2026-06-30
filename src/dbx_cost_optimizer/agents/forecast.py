"""Forecast & ROI Agent — tier 2.

Projects baseline run-rate from daily trend; annotates portfolio totals.
No external deps — simple linear/mean estimators. Swap for Prophet/ARIMA later.
"""
from __future__ import annotations

from typing import List

from ..models import Finding
from ..registry import register_agent
from .base import BaseAgent


@register_agent
class ForecastAgent(BaseAgent):
    name = "forecast"
    requires = ["daily_trend"]
    tier = 2

    def run(self, ctx) -> List[Finding]:
        trend = ctx.get_facts("daily_trend")
        costs = [float(r.get("cost_usd") or 0.0) for r in trend]
        if costs:
            avg_daily = sum(costs) / len(costs)
            recent = costs[-7:] if len(costs) >= 7 else costs
            recent_avg = sum(recent) / len(recent)
            slope = (recent_avg - avg_daily)
            projected_monthly = round(recent_avg * 30, 2)
        else:
            avg_daily = recent_avg = slope = projected_monthly = 0.0

        ctx.meta["forecast"] = {
            "avg_daily_usd": round(avg_daily, 2),
            "recent_7d_avg_usd": round(recent_avg, 2),
            "trend_slope_usd_per_day": round(slope, 2),
            "projected_monthly_usd": projected_monthly,
            "identified_monthly_savings_usd": ctx.total_identified_savings(),
        }
        return []  # forecast annotates meta, emits no findings
