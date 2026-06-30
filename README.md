# Databricks Cost Optimizer

Multi-agent system that estimates Databricks spend, finds cost reductions, ranks them by
ROI, and **emails alerts** when spend/waste crosses a threshold. Runs against live System
Tables or canned fixtures (mock mode, no workspace needed).

## Architecture

```
Orchestrator (supervisor)
  tier 0  telemetry        -> runs System Tables SQL, writes normalized facts
  tier 1  compute          -> idle/oversized clusters, autoterminate, wrong cluster type
          job_query        -> failed-run waste, batch-eligible, spill, repeated queries
          storage          -> OPTIMIZE / clustering / version bloat
  tier 2  forecast         -> baseline run-rate + projected monthly spend
          report           -> rank findings by (savings*confidence/effort), render MD+JSON
          pdf_report       -> PDF grouped by fix type: issue + fix + official docs link
  tier 3  alert            -> evaluate thresholds, email recipient list on breach
```

Shared `ContextStore` is the single source of truth. All dollar figures come from
deterministic tools (`tools/`), never from an LLM.

## Install

```bash
pip install -e .                       # core
pip install -e '.[databricks]'         # + live System Tables connector
pip install -e '.[llm]'                # + optional Claude narrative
pip install -e '.[pdf]'                # + PDF report (reportlab)
pip install -e '.[all]'                # everything incl. pytest
```

## Run

```bash
dbxopt run --mock                      # full pass on fixtures, prints report
dbxopt run --mock --out ctx.json       # also dump full context
dbxopt run                             # live (needs .env Databricks creds)
dbxopt alert --dry-run-email           # evaluate thresholds, print would-be email
dbxopt agents                          # list registered agents
```

Copy `.env.example` -> `.env` and fill Databricks + SMTP creds.

## Email alerts

`AlertAgent` (tier 3) checks rules in `agents/alert.py`:
- `monthly_spend_projection` — projected monthly spend > `ALERT_MONTHLY_SPEND_USD` (critical)
- `single_entity_spend` — any cluster/job/warehouse > `ALERT_SINGLE_ENTITY_USD` (warning)
- `recoverable_waste` — total identified savings > `ALERT_IDENTIFIED_WASTE_USD` (warning)

On breach it emails `ALERT_RECIPIENTS` (comma-separated) via SMTP, HTML + plaintext.
`dbxopt alert` exits non-zero when alerts fire — drop it in cron/CI.

## Extend (the point of the design)

**New analysis agent:**
```python
from dbx_cost_optimizer.agents.base import BaseAgent
from dbx_cost_optimizer.registry import register_agent
from dbx_cost_optimizer.models import Finding

@register_agent
class ServerlessFitAgent(BaseAgent):
    name = "serverless_fit"
    requires = ["expensive_jobs"]
    tier = 1
    def run(self, ctx):
        # read ctx.get_facts(...), return [Finding(...)]
        return []
```
Add `"serverless_fit"` to the crew (or pass `crew=[...]` to `Orchestrator`). Done.

## PDF report

`PdfReportAgent` (tier 2) dispatches on each `Finding.category` via `docs_catalog.py`,
groups findings by **fix family** (Compute right-sizing, Storage maintenance, Query
tuning, Job configuration), and writes a PDF where every finding shows: issue/evidence,
the exact fix, rollback, a plain "how it works", and a **clickable official
docs.databricks.com link**. Output path = `DBX_PDF_PATH` (default `dbx_cost_report.pdf`).
Falls back to Markdown if `reportlab` isn't installed. Add a mapping for a new fix type
by adding a `DocEntry` to `docs_catalog.CATALOG`.

**New data source:** implement `connectors/base.Connector.query`.
**New alert channel:** implement `notifications/base.Notifier.send` (e.g. Slack).
**New alert rule:** `alert_agent.add_rule(fn)` where `fn(ctx, thresholds) -> AlertEvent|None`.
**New SQL:** add to `sql/queries.py` with a `-- query: <name>` marker.

## Test

```bash
pytest -q
```

## Notes / production gaps

- `pricing.default` is **list price**. Swap in your contracted/commit rate table.
- File-level stats (small files, version bloat) aren't in System Tables — `StorageAgent`
  should call `DESCRIBE DETAIL` / `DESCRIBE HISTORY` per table in production.
- Column names vary by cloud (`aws_attributes` vs `azure_attributes`) — verify schema.
