---
skill: alerting_and_delivery
agent: [alert, sink, dashboard, genie, pdf_report]
fix_family: Delivery
categories: []
---
# Alerting & delivery

## Purpose
Turn findings into action: notify, persist, visualize, converse.

## Capabilities
- **alert** — evaluate USD thresholds; email the recipient list on breach (HTML+text).
- **sink** — write findings + daily usage to Delta tables (`cost_findings`, `cost_usage_daily`).
- **dashboard** — build an AI/BI (Lakeview) dashboard over those tables.
- **genie** — interactive natural-language Q&A over the cost data.
- **pdf_report** — per-finding PDF: issue, fix, official docs link.

## Thresholds (USD)
- `monthly_spend_projection` (critical)
- `single_entity_spend` (warning)
- `recoverable_waste` (warning)

## Extend
- New channel: implement `notifications/base.Notifier.send` (e.g. Slack).
- New rule: `alert_agent.add_rule(fn)`.
