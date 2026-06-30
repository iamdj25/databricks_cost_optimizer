"""End-to-end smoke test on mock fixtures — no Databricks, no SMTP."""
from dbx_cost_optimizer.config import Settings
from dbx_cost_optimizer.orchestrator import Orchestrator


def _run():
    orch = Orchestrator(Settings.load(), mock=True)
    orch.alert_dry_run = True   # print instead of send
    return orch.run()


def test_pipeline_produces_findings():
    ctx = _run()
    assert len(ctx.get_findings()) > 0
    assert ctx.meta["telemetry_row_counts"]["idle_clusters"] == 2


def test_forecast_and_report_populated():
    ctx = _run()
    assert ctx.meta["forecast"]["projected_monthly_usd"] > 0
    assert "Ranked recommendations" in ctx.meta["report_md"]


def test_alerts_fire_and_email_dry_run():
    ctx = _run()
    # fixtures + default thresholds should breach at least one rule
    assert ctx.meta["alert_event_count"] >= 1
    assert ctx.meta.get("alert_email_sent") is True  # dry-run returns True


def test_findings_ranked_by_priority():
    ctx = _run()
    fs = ctx.meta["report_json"]
    pr = [f["priority"] for f in fs]
    assert pr == sorted(pr, reverse=True)


def test_registry_extensible():
    from dbx_cost_optimizer.registry import list_agents
    for name in ["telemetry", "compute", "job_query", "storage", "forecast",
                 "report", "pdf_report", "alert"]:
        assert name in list_agents()


def test_pdf_report_generated(tmp_path):
    import os
    out = tmp_path / "report.pdf"
    os.environ["DBX_PDF_PATH"] = str(out)
    try:
        ctx = _run()
    finally:
        os.environ.pop("DBX_PDF_PATH", None)
    path = ctx.meta.get("pdf_report_path")
    assert path and os.path.exists(path)
    with open(path, "rb") as fh:
        head = fh.read(5)
    # real PDF if reportlab present, else markdown fallback
    assert head == b"%PDF-" or path.endswith(".md")


def test_pdf_groups_by_fix_family():
    from dbx_cost_optimizer.docs_catalog import lookup
    assert lookup("no_autoterminate").fix_family == "Compute right-sizing"
    assert lookup("repeated_query").fix_family == "Query tuning"
    # unknown category still yields a usable doc link
    assert lookup("totally_new_rule").url.startswith("https://docs.databricks.com")
