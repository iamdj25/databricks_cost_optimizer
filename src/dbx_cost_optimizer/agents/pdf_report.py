"""PDF Report Agent — tier 2.

Generates a PDF that, for each finding, states the issue, the possible fix, and a
link to the official Databricks documentation explaining how that mechanism works.
Dispatches on `Finding.category` via docs_catalog, then groups findings by fix
family so the report is organized by the type of fix needed.

Requires reportlab: pip install 'dbx-cost-optimizer[pdf]'. If absent, the agent
writes a Markdown fallback and records the reason instead of crashing.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Dict, List

from ..docs_catalog import lookup
from ..models import Finding
from ..registry import register_agent
from .base import BaseAgent

_SEVERITY_BY_RISK = {"High": "#c0392b", "Med": "#e67e22", "Low": "#27ae60"}


@register_agent
class PdfReportAgent(BaseAgent):
    name = "pdf_report"
    requires: List[str] = []     # operates on findings already in ctx
    tier = 2

    def run(self, ctx) -> List[Finding]:
        findings = sorted(ctx.get_findings(), key=lambda f: f.priority, reverse=True)
        if not findings:
            ctx.meta["pdf_report_path"] = None
            ctx.meta["pdf_report_note"] = "no findings to report"
            return []

        path = self.settings.pdf_output_path
        try:
            self._render_pdf(path, findings, ctx)
            ctx.meta["pdf_report_path"] = path
        except ImportError as e:
            fallback = path.rsplit(".", 1)[0] + ".md"
            self._render_markdown(fallback, findings, ctx)
            ctx.meta["pdf_report_path"] = fallback
            ctx.meta["pdf_report_note"] = f"reportlab missing ({e}); wrote Markdown fallback"
        return []

    # ---- grouping: organize by the type of fix ----
    @staticmethod
    def _group(findings: List[Finding]) -> Dict[str, List[Finding]]:
        groups: Dict[str, List[Finding]] = defaultdict(list)
        for f in findings:
            groups[lookup(f.category).fix_family].append(f)
        return dict(sorted(groups.items()))

    # ---- PDF renderer (reportlab) ----
    def _render_pdf(self, path: str, findings: List[Finding], ctx) -> None:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_LEFT
        from reportlab.lib.pagesizes import LETTER
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import inch
        from reportlab.platypus import (HRFlowable, ListFlowable, ListItem,
                                        Paragraph, SimpleDocTemplate, Spacer)

        ss = getSampleStyleSheet()
        h1 = ParagraphStyle("h1", parent=ss["Title"], fontSize=20, spaceAfter=6)
        h2 = ParagraphStyle("h2", parent=ss["Heading2"], textColor=colors.HexColor("#1b4f72"),
                            spaceBefore=14, spaceAfter=4)
        h3 = ParagraphStyle("h3", parent=ss["Heading3"], fontSize=11.5, spaceBefore=8, spaceAfter=2)
        body = ParagraphStyle("body", parent=ss["BodyText"], fontSize=9.5, leading=13, alignment=TA_LEFT)
        mono = ParagraphStyle("mono", parent=body, fontName="Courier", fontSize=8.5,
                              backColor=colors.HexColor("#f4f4f4"), leftIndent=4, spaceBefore=2, spaceAfter=4)
        link = ParagraphStyle("link", parent=body, textColor=colors.HexColor("#2471a3"))

        story = []
        fc = ctx.meta.get("forecast", {})
        total = ctx.total_identified_savings()
        story.append(Paragraph("Databricks Cost Optimization Report", h1))
        story.append(Paragraph(
            f"Projected monthly spend: <b>${fc.get('projected_monthly_usd', 0):,.0f}</b> &nbsp;|&nbsp; "
            f"Identified recoverable savings: <b>${total:,.0f}/mo</b> &nbsp;|&nbsp; "
            f"{len(findings)} findings", body))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#cccccc"),
                                spaceBefore=6, spaceAfter=4))

        for family, items in self._group(findings).items():
            fam_savings = sum(f.monthly_savings_usd for f in items)
            story.append(Paragraph(f"{family} &nbsp;—&nbsp; ${fam_savings:,.0f}/mo ({len(items)})", h2))
            for f in items:
                doc = lookup(f.category)
                risk_color = _SEVERITY_BY_RISK.get(f.risk, "#333333")
                story.append(Paragraph(
                    f"{f.recommendation}", h3))
                story.append(Paragraph(
                    f"<b>Target:</b> {f.target_type}:{f.target_id} &nbsp;|&nbsp; "
                    f"<b>Savings:</b> ${f.monthly_savings_usd:,.0f}/mo &nbsp;|&nbsp; "
                    f"<b>Effort:</b> {f.effort} &nbsp;|&nbsp; "
                    f'<b>Risk:</b> <font color="{risk_color}">{f.risk}</font> &nbsp;|&nbsp; '
                    f"<b>Confidence:</b> {f.confidence:.0%}", body))
                story.append(Paragraph("<b>Issue (evidence):</b> " +
                                       ", ".join(f"{k}={v}" for k, v in f.evidence.items()), body))
                story.append(Paragraph("<b>Possible fix:</b>", body))
                story.append(Paragraph(f.exact_change or "(see recommendation)", mono))
                story.append(Paragraph(f"<b>Rollback:</b> {f.rollback or 'n/a'}", body))
                story.append(Paragraph(
                    f'<b>How it works:</b> {doc.how_it_works}', body))
                story.append(Paragraph(
                    f'<b>Official docs:</b> <a href="{doc.url}"><u>{doc.title}</u></a><br/>'
                    f'<font size=7 color="#7f8c8d">{doc.url}</font>', link))
                story.append(Spacer(1, 6))
            story.append(Spacer(1, 4))

        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#dddddd")))
        story.append(Paragraph(
            '<font size=7 color="#95a5a6">Generated by dbx-cost-optimizer. Dollar figures are '
            'tool-computed estimates; doc links point at docs.databricks.com (verify per cloud).</font>',
            body))

        SimpleDocTemplate(path, pagesize=LETTER, leftMargin=0.7 * inch, rightMargin=0.7 * inch,
                          topMargin=0.7 * inch, bottomMargin=0.6 * inch,
                          title="Databricks Cost Optimization Report").build(story)

    # ---- Markdown fallback (no reportlab) ----
    def _render_markdown(self, path: str, findings: List[Finding], ctx) -> None:
        lines = ["# Databricks Cost Optimization Report", ""]
        for family, items in self._group(findings).items():
            lines.append(f"## {family}")
            for f in items:
                doc = lookup(f.category)
                lines += [
                    f"### {f.recommendation}",
                    f"- target: `{f.target_type}:{f.target_id}` | savings ${f.monthly_savings_usd:,.0f}/mo "
                    f"| effort {f.effort} | risk {f.risk} | conf {f.confidence:.0%}",
                    f"- issue: {', '.join(f'{k}={v}' for k, v in f.evidence.items())}",
                    f"- fix: `{f.exact_change}`",
                    f"- rollback: {f.rollback}",
                    f"- how it works: {doc.how_it_works}",
                    f"- docs: [{doc.title}]({doc.url})",
                    "",
                ]
        with open(path, "w") as fh:
            fh.write("\n".join(lines))
