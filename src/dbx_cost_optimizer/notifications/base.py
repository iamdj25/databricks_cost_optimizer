"""Notifier interface. Add Slack/PagerDuty/Teams by implementing `send`."""
from __future__ import annotations

import abc
from typing import List

from ..models import AlertEvent


class Notifier(abc.ABC):
    @abc.abstractmethod
    def send(self, subject: str, body_text: str, body_html: str = "") -> bool:
        """Return True on success."""

    def notify_alerts(self, events: List[AlertEvent], report_md: str = "") -> bool:
        if not events:
            return False
        crit = sum(1 for e in events if e.severity == "critical")
        subject = f"[Databricks Cost] {len(events)} alert(s)" + (f", {crit} critical" if crit else "")
        text = self.render_text(events, report_md)
        html = self.render_html(events, report_md)
        return self.send(subject, text, html)

    @staticmethod
    def render_text(events: List[AlertEvent], report_md: str) -> str:
        lines = ["Databricks Cost Optimizer — threshold alerts", "=" * 44, ""]
        for e in events:
            lines.append(f"[{e.severity.upper()}] {e.rule}")
            lines.append(f"  {e.message}")
            lines.append(f"  value=${e.value_usd:,.0f}  threshold=${e.threshold_usd:,.0f}")
            lines.append("")
        if report_md:
            lines += ["", "--- Top recommendations ---", report_md]
        return "\n".join(lines)

    @staticmethod
    def render_html(events: List[AlertEvent], report_md: str) -> str:
        color = {"critical": "#c0392b", "warning": "#e67e22", "info": "#2980b9"}
        rows = ""
        for e in events:
            rows += (
                f'<tr style="border-bottom:1px solid #eee">'
                f'<td style="padding:6px;color:{color.get(e.severity, "#333")};font-weight:600">{e.severity.upper()}</td>'
                f'<td style="padding:6px">{e.rule}</td>'
                f'<td style="padding:6px">{e.message}</td>'
                f'<td style="padding:6px;text-align:right">${e.value_usd:,.0f}</td>'
                f'<td style="padding:6px;text-align:right">${e.threshold_usd:,.0f}</td></tr>'
            )
        return (
            '<div style="font-family:Arial,sans-serif">'
            '<h2 style="margin:0 0 8px">Databricks Cost Optimizer — Alerts</h2>'
            '<table style="border-collapse:collapse;width:100%">'
            '<tr style="background:#f5f5f5"><th style="padding:6px;text-align:left">Severity</th>'
            '<th style="padding:6px;text-align:left">Rule</th><th style="padding:6px;text-align:left">Message</th>'
            '<th style="padding:6px;text-align:right">Value</th><th style="padding:6px;text-align:right">Threshold</th></tr>'
            f'{rows}</table></div>'
        )
