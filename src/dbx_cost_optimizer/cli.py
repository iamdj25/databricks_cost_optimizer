"""CLI entrypoint: `dbxopt`."""
from __future__ import annotations

import argparse
import json
import sys

from .config import Settings
from .orchestrator import Orchestrator


def _add_common(p):
    p.add_argument("--mock", action="store_true", help="Use canned fixtures (no Databricks).")
    p.add_argument("--no-email", action="store_true", help="Do not send alert emails.")
    p.add_argument("--dry-run-email", action="store_true", help="Print emails instead of sending.")


def cmd_run(args) -> int:
    orch = Orchestrator(Settings.load(), mock=args.mock)
    orch.alert_dry_run = args.dry_run_email
    orch.alert_send_email = not args.no_email
    ctx = orch.run()

    print(ctx.meta.get("report_md", "(no report)"))
    print("\n--- summary ---")
    print(json.dumps({
        "projected_monthly_usd": ctx.meta.get("forecast", {}).get("projected_monthly_usd"),
        "identified_savings_usd": ctx.total_identified_savings(),
        "findings": len(ctx.get_findings()),
        "alerts": ctx.meta.get("alert_event_count", 0),
        "alert_email_sent": ctx.meta.get("alert_email_sent"),
        "skipped_agents": ctx.meta.get("skipped_agents", []),
    }, indent=2))
    if args.out:
        ctx.dump(args.out)
        print(f"\nWrote full context to {args.out}")
    return 0


def cmd_alert(args) -> int:
    """Run pipeline but only surface alerts (still needs telemetry+forecast)."""
    orch = Orchestrator(Settings.load(), mock=args.mock)
    orch.alert_dry_run = args.dry_run_email
    orch.alert_send_email = not args.no_email
    ctx = orch.run()
    alerts = [a.to_dict() for a in ctx.get_alerts()]
    print(json.dumps({"alerts": alerts, "email_sent": ctx.meta.get("alert_email_sent")}, indent=2))
    return 0 if not alerts else 2  # non-zero exit when alerts fire (CI/cron friendly)


def cmd_agents(_args) -> int:
    print("\n".join(Orchestrator.available_agents()))
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="dbxopt", description="Databricks cost optimizer")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_run = sub.add_parser("run", help="Full optimization pass + report.")
    _add_common(p_run)
    p_run.add_argument("--out", help="Write full context JSON to this path.")
    p_run.set_defaults(func=cmd_run)

    p_alert = sub.add_parser("alert", help="Evaluate thresholds, email on breach.")
    _add_common(p_alert)
    p_alert.set_defaults(func=cmd_alert)

    p_agents = sub.add_parser("agents", help="List registered agents.")
    p_agents.set_defaults(func=cmd_agents)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
