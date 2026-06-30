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
    p.add_argument("--profile", help="~/.databrickscfg profile to use (Databricks CLI).")


def _settings(args) -> Settings:
    s = Settings.load()
    if getattr(args, "profile", None):
        s.databricks.profile = args.profile
    return s


def cmd_run(args) -> int:
    orch = Orchestrator(_settings(args), mock=args.mock)
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
        "pdf_report_path": ctx.meta.get("pdf_report_path"),
        "skipped_agents": ctx.meta.get("skipped_agents", []),
    }, indent=2))
    if args.out:
        ctx.dump(args.out)
        print(f"\nWrote full context to {args.out}")
    return 0


def cmd_alert(args) -> int:
    """Run pipeline but only surface alerts (still needs telemetry+forecast)."""
    orch = Orchestrator(_settings(args), mock=args.mock)
    orch.alert_dry_run = args.dry_run_email
    orch.alert_send_email = not args.no_email
    ctx = orch.run()
    alerts = [a.to_dict() for a in ctx.get_alerts()]
    print(json.dumps({"alerts": alerts, "email_sent": ctx.meta.get("alert_email_sent")}, indent=2))
    return 0 if not alerts else 2  # non-zero exit when alerts fire (CI/cron friendly)


def cmd_publish(args) -> int:
    """Full pass -> write Delta tables -> create AI/BI dashboard."""
    settings = _settings(args)
    orch = Orchestrator(settings, mock=args.mock)
    orch.alert_send_email = not args.no_email
    orch.alert_dry_run = args.dry_run_email
    ctx = orch.run()  # sink agent materializes tables (skipped if mock)

    from .agents.dashboard import DashboardAgent
    dash = DashboardAgent(settings, orch.connector)
    dash.run(ctx)

    print(json.dumps({
        "findings_table": ctx.meta.get("sink_findings_table"),
        "usage_table": ctx.meta.get("sink_usage_table"),
        "sink_rows": ctx.meta.get("sink_rows"),
        "dashboard_id": ctx.meta.get("dashboard_id"),
        "dashboard_url": ctx.meta.get("dashboard_url"),
        "dashboard_error": ctx.meta.get("dashboard_error"),
        "sink_note": ctx.meta.get("sink_note"),
    }, indent=2))
    return 0


def cmd_dashboard(args) -> int:
    settings = _settings(args)
    orch = Orchestrator(settings, mock=args.mock)
    ctx = orch.run()
    from .agents.dashboard import DashboardAgent
    DashboardAgent(settings, orch.connector).run(ctx)
    print(json.dumps({"dashboard_id": ctx.meta.get("dashboard_id"),
                      "dashboard_url": ctx.meta.get("dashboard_url"),
                      "error": ctx.meta.get("dashboard_error")}, indent=2))
    return 0


def cmd_genie(args) -> int:
    """Interactive Genie REPL over the cost tables."""
    settings = _settings(args)
    from .agents.genie import GenieAgent
    from .connectors import build_connector

    agent = GenieAgent(settings, build_connector(settings, mock=False))
    try:
        space = agent.ensure_space()
    except Exception as e:
        print(f"Genie not ready: {e}")
        return 1

    if args.ask:
        ans = agent.ask(args.ask)
        print(json.dumps(ans.to_dict(), indent=2))
        return 0

    print(f"Genie space {space}. Ask questions about your Databricks cost. "
          "Type 'reset' for a new conversation, 'exit' to quit.")
    while True:
        try:
            q = input("genie> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not q:
            continue
        if q in {"exit", "quit"}:
            break
        if q == "reset":
            agent.reset()
            print("(new conversation)")
            continue
        ans = agent.ask(q)
        if ans.error:
            print(f"  error: {ans.error}")
            continue
        if ans.text:
            print(f"  {ans.text}")
        if ans.sql:
            print(f"  SQL: {ans.sql}")
        if ans.rows:
            if ans.columns:
                print("  " + " | ".join(ans.columns))
            for row in ans.rows[:20]:
                print("  " + " | ".join(str(c) for c in row))
    return 0


def cmd_agents(_args) -> int:
    print("\n".join(Orchestrator.available_agents()))
    return 0


def cmd_skills(args) -> int:
    from .skills import load_skills
    skills = load_skills()
    if args.show:
        print(skills[args.show].body if args.show in skills else f"unknown skill {args.show}")
        return 0
    for name, s in skills.items():
        agents = ",".join(s.agent) if s.agent else "-"
        print(f"{name:24} family={s.fix_family or '-':22} agent={agents}")
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

    p_pub = sub.add_parser("publish", help="Run + write Delta tables + create AI/BI dashboard.")
    _add_common(p_pub)
    p_pub.set_defaults(func=cmd_publish)

    p_dash = sub.add_parser("dashboard", help="Create/refresh the AI/BI dashboard only.")
    _add_common(p_dash)
    p_dash.set_defaults(func=cmd_dashboard)

    p_genie = sub.add_parser("genie", help="Interactive Genie Q&A over cost tables.")
    p_genie.add_argument("--profile", help="~/.databrickscfg profile.")
    p_genie.add_argument("--ask", help="Single question (non-interactive).")
    p_genie.set_defaults(func=cmd_genie)

    p_agents = sub.add_parser("agents", help="List registered agents.")
    p_agents.set_defaults(func=cmd_agents)

    p_skills = sub.add_parser("skills", help="List skill cards (or --show <name>).")
    p_skills.add_argument("--show", help="Print one skill card body.")
    p_skills.set_defaults(func=cmd_skills)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
