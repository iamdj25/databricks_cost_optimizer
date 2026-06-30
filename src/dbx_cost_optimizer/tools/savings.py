"""Deterministic savings math. Agents call these — never compute $ in prose/LLM."""
from __future__ import annotations


def savings_from_runtime(current_cost_usd: float, duration_before_s: float,
                         duration_after_s: float) -> float:
    """Cost scales with runtime. Savings = cost * (1 - after/before)."""
    if duration_before_s <= 0 or duration_after_s < 0:
        return 0.0
    frac = max(0.0, 1.0 - (duration_after_s / duration_before_s))
    return round(current_cost_usd * frac, 2)


def savings_from_cost_fraction(current_cost_usd: float, reducible_fraction: float) -> float:
    """Generic: a fraction of the entity's cost is eliminated."""
    return round(current_cost_usd * max(0.0, min(1.0, reducible_fraction)), 2)
