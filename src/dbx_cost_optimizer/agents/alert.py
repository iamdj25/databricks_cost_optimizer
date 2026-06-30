"""Alert Agent — tier 3.

Evaluates threshold rules against the shared context. On breach, builds AlertEvents
and emails the recipient list. Rules are pluggable: append to AlertAgent.rules or
pass `extra_rules`.
"""
from __future__ import annotations

from typing import Callable, List, Optional

from ..models import AlertEvent, Finding
from ..notifications.base import Notifier
from ..notifications.email import EmailNotifier
from ..registry import register_agent
from .base import BaseAgent

# A rule: (ctx, thresholds) -> Optional[AlertEvent]
Rule = Callable[["object", "object"], Optional[AlertEvent]]


def rule_monthly_spend(ctx, th) -> Optional[AlertEvent]:
    fc = ctx.meta.get("forecast", {})
    projected = float(fc.get("projected_monthly_usd", 0.0))
    if projected > th.monthly_spend_usd:
        return AlertEvent(
            rule="monthly_spend_projection",
            severity="critical",
            message=f"Projected monthly spend ${projected:,.0f} exceeds budget ${th.monthly_spend_usd:,.0f}.",
            value_usd=projected, threshold_usd=th.monthly_spend_usd,
            context={"recent_7d_avg_usd": fc.get("recent_7d_avg_usd")},
        )
    return None


def rule_single_entity(ctx, th) -> Optional[AlertEvent]:
    rows = ctx.get_facts("cost_by_entity")
    if not rows:
        return None
    top = max(rows, key=lambda r: float(r.get("cost_usd") or 0.0))
    cost = float(top.get("cost_usd") or 0.0)
    if cost > th.single_entity_usd:
        eid = top.get("cluster_id") or top.get("job_id") or top.get("warehouse_id") or "unknown"
        return AlertEvent(
            rule="single_entity_spend",
            severity="warning",
            message=f"Entity {eid} ({top.get('product')}) cost ${cost:,.0f} exceeds ${th.single_entity_usd:,.0f}.",
            value_usd=cost, threshold_usd=th.single_entity_usd,
            context={"entity": eid, "product": top.get("product")},
        )
    return None


def rule_identified_waste(ctx, th) -> Optional[AlertEvent]:
    waste = ctx.total_identified_savings()
    if waste > th.identified_waste_usd:
        return AlertEvent(
            rule="recoverable_waste",
            severity="warning",
            message=f"Optimizer found ${waste:,.0f}/mo recoverable — above ${th.identified_waste_usd:,.0f} action threshold.",
            value_usd=waste, threshold_usd=th.identified_waste_usd,
            context={"finding_count": len(ctx.get_findings())},
        )
    return None


DEFAULT_RULES: List[Rule] = [rule_monthly_spend, rule_single_entity, rule_identified_waste]


@register_agent
class AlertAgent(BaseAgent):
    name = "alert"
    requires: List[str] = []   # tolerant: evaluates whatever facts exist
    tier = 3

    #: set by orchestrator/tests to inject a notifier or disable sending
    notifier: Optional[Notifier] = None
    dry_run: bool = False
    send_email: bool = True

    def __init__(self, settings, connector) -> None:
        super().__init__(settings, connector)
        self.rules: List[Rule] = list(DEFAULT_RULES)

    def add_rule(self, rule: Rule) -> None:
        self.rules.append(rule)

    def _build_notifier(self) -> Notifier:
        if self.notifier is not None:
            return self.notifier
        return EmailNotifier(self.settings.smtp, dry_run=self.dry_run)

    def run(self, ctx) -> List[Finding]:
        events: List[AlertEvent] = []
        for rule in self.rules:
            try:
                ev = rule(ctx, self.settings.thresholds)
            except Exception as e:
                ctx.meta.setdefault("alert_errors", []).append(f"{getattr(rule, '__name__', rule)}: {e}")
                ev = None
            if ev:
                events.append(ev)
                ctx.add_alert(ev)

        ctx.meta["alert_event_count"] = len(events)
        if events and self.send_email:
            try:
                notifier = self._build_notifier()
                report_md = ctx.meta.get("report_md_brief", "")
                sent = notifier.notify_alerts(events, report_md)
                ctx.meta["alert_email_sent"] = bool(sent)
            except Exception as e:
                ctx.meta["alert_email_error"] = str(e)
                ctx.meta["alert_email_sent"] = False
        return []  # alert emits events into ctx, not findings
