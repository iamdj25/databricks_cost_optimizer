"""Report Agent — tier 2. Ranks findings, renders markdown + JSON.

Optional LLM narrative (Anthropic) if `anthropic` installed and key set — purely
cosmetic; all numbers come from findings, never the model.
"""
from __future__ import annotations

from typing import List

from ..models import Finding
from ..registry import register_agent
from .base import BaseAgent


@register_agent
class ReportAgent(BaseAgent):
    name = "report"
    requires: List[str] = []
    tier = 2

    def run(self, ctx) -> List[Finding]:
        findings = sorted(ctx.get_findings(), key=lambda f: f.priority, reverse=True)
        total = ctx.total_identified_savings()
        fc = ctx.meta.get("forecast", {})

        md = [f"# Databricks Cost Optimizer — Report",
              "",
              f"**Projected monthly spend:** ${fc.get('projected_monthly_usd', 0):,.0f}",
              f"**Identified recoverable savings:** ${total:,.0f}/mo across {len(findings)} findings",
              "",
              "## Ranked recommendations", ""]
        for i, f in enumerate(findings, 1):
            md.append(
                f"### {i}. {f.recommendation}\n"
                f"- target: `{f.target_type}:{f.target_id}`\n"
                f"- savings: **${f.monthly_savings_usd:,.0f}/mo** | effort: {f.effort} | "
                f"risk: {f.risk} | confidence: {f.confidence:.0%} | priority: {f.priority:.1f}\n"
                f"- change: `{f.exact_change}`\n"
                f"- rollback: {f.rollback}\n"
            )

        report_md = "\n".join(md)
        ctx.meta["report_md"] = report_md

        # brief: top 5 for email body
        brief = ["Top recommendations:"]
        for i, f in enumerate(findings[:5], 1):
            brief.append(f"{i}. ${f.monthly_savings_usd:,.0f}/mo — {f.recommendation} ({f.effort}/{f.risk})")
        ctx.meta["report_md_brief"] = "\n".join(brief)

        ctx.meta["report_json"] = [f.to_dict() for f in findings]
        return []
