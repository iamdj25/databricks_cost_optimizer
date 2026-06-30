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
dbxopt run                             # live (env or CLI profile auth)
dbxopt run --profile prod              # use a ~/.databrickscfg profile
dbxopt alert --dry-run-email           # evaluate thresholds, print would-be email
dbxopt publish                         # run + write Delta tables + create dashboard
dbxopt dashboard                       # (re)create the AI/BI dashboard
dbxopt genie                           # interactive Genie Q&A (REPL)
dbxopt genie --ask "top 3 fix families by savings"
dbxopt agents                          # list registered agents
dbxopt skills                          # list skill cards  (--show <name> for one)
```

Copy `.env.example` -> `.env`, or just log in with the Databricks CLI
(`databricks auth login`) and pass `--profile`. Auth resolution:
env creds → `~/.databrickscfg` profile → mock.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the high-level diagram.

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

## Deploy as a Databricks Asset Bundle (DAB)

Run the optimizer as a scheduled **job** that writes findings to Delta and renders
a **dashboard** — all in your workspace.

```bash
databricks auth login --host https://<workspace>      # one-time
# edit databricks.yml host + set vars (warehouse_id, catalog, schema, node_type_id)
databricks secrets create-scope cost_optimizer
databricks secrets put-secret cost_optimizer warehouse_id      # paste warehouse id
databricks bundle validate -t dev
databricks bundle deploy -t dev                       # builds wheel, uploads, creates job+dashboard
databricks bundle run cost_optimizer_job -t dev       # run now (else daily 06:00 UTC)
```

What deploys:
- **Job** (`resources/optimizer_job.yml`) — runs `dbxopt run` on a job cluster. Inside
  Databricks the Spark connector hits System Tables with the job identity's perms (no token),
  and the `sink` agent writes `cost_findings` + `cost_usage_daily`.
- **Dashboard** (`resources/cost_dashboard.yml` + `cost_dashboard.lvdash.json`) — AI/BI
  Lakeview dashboard: savings KPIs, savings-by-fix-family, spend trend, ranked table.
- Notebook alternative: `notebooks/run_optimizer.py`.

## Genie (interactive)

Two delivery agents back the conversational layer:
- **dashboard** agent — creates the AI/BI dashboard via the Lakeview API.
- **genie** agent — drives an interactive Genie space over the cost tables.

One-time: in the Databricks UI create a **Genie space** over `cost_findings`,
`cost_usage_daily`, and `system.billing.usage`; set `DBX_GENIE_SPACE_ID`. Then:

```bash
dbxopt genie
genie> which clusters waste the most money?
genie> how much can we save by fixing auto-termination?
genie> reset          # new conversation
```

Follow-ups keep conversation context. Each answer returns Genie's text, the
generated SQL, and result rows. `--ask` gives a one-shot non-interactive answer.

## Skills

`skills/*.md` are capability playbook cards (when-to-use, signals, fix, docs) that
the agents map to via `Finding.category`. List with `dbxopt skills`; load in code
with `dbx_cost_optimizer.skills.load_skills()` / `skill_for_category(cat)`. Add a
card → auto-discovered.

## Test

```bash
pytest -q
```

## Notes / production gaps

- `pricing.default` is **list price**. Swap in your contracted/commit rate table.
- File-level stats (small files, version bloat) aren't in System Tables — `StorageAgent`
  should call `DESCRIBE DETAIL` / `DESCRIBE HISTORY` per table in production.
- Column names vary by cloud (`aws_attributes` vs `azure_attributes`) — verify schema.
