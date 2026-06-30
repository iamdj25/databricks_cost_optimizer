"""Job / Query Performance Agent — tier 1."""
from __future__ import annotations

from typing import List

from ..models import Finding
from ..registry import register_agent
from ..tools.savings import savings_from_cost_fraction, savings_from_runtime
from .base import BaseAgent

_SMALL_FILE_BYTES = 64 * 1024 * 1024
_SPILL_BYTES = 1 * 1024 * 1024 * 1024  # 1GB spill = real memory pressure


@register_agent
class JobQueryAgent(BaseAgent):
    name = "job_query"
    requires = ["expensive_jobs", "slow_queries"]
    tier = 1

    def run(self, ctx) -> List[Finding]:
        findings: List[Finding] = []

        # failed/retried runs -> wasted DBU
        failed_by_job = {}
        for r in ctx.get_facts("failed_runs"):
            failed_by_job[str(r["job_id"])] = failed_by_job.get(str(r["job_id"]), 0) + int(r.get("runs") or 0)

        for j in ctx.get_facts("expensive_jobs"):
            jid = str(j["job_id"])
            cost = float(j.get("cost_usd") or 0.0)
            runs = int(j.get("run_count") or 1)
            fails = failed_by_job.get(jid, 0)

            if fails and runs:
                waste_frac = min(0.5, fails / runs)
                saving = savings_from_cost_fraction(cost, waste_frac)
                findings.append(Finding(
                    agent=self.name, category="failed_run_waste", target_type="job", target_id=jid,
                    recommendation=f"Job {jid}: {fails}/{runs} runs fail/retry — fix root cause to stop burning DBU.",
                    monthly_savings_usd=saving, effort="M", risk="Low", confidence=0.7,
                    evidence={"failed_runs": fails, "total_runs": runs},
                    exact_change="Inspect termination_code; add retry cap / fix driver error.",
                    rollback="n/a (reliability fix).",
                ))

            # high-frequency short job -> batch candidate
            if runs > 200 and float(j.get("avg_dur_s") or 0) < 300:
                saving = savings_from_cost_fraction(cost, 0.25)
                findings.append(Finding(
                    agent=self.name, category="batch_eligible", target_type="job", target_id=jid,
                    recommendation=f"Job {jid} runs {runs}x at {j.get('avg_dur_s')}s avg — batch / trigger-based to cut startup overhead.",
                    monthly_savings_usd=saving, effort="M", risk="Med", confidence=0.55,
                    evidence={"run_count": runs, "avg_dur_s": j.get("avg_dur_s")},
                    exact_change="Switch schedule to file-arrival trigger or coarser interval.",
                    rollback="Restore original cron schedule.",
                ))

        # slow / spilling / scan-heavy queries
        for q in ctx.get_facts("slow_queries"):
            read_files = int(q.get("read_files") or 0)
            spilled = int(q.get("spilled_local_bytes") or 0)
            dur = float(q.get("total_duration_ms") or 0)
            # crude per-query cost proxy not available; tie to warehouse via fraction of its cost later.
            if read_files > 10000:
                findings.append(Finding(
                    agent=self.name, category="small_files_scan", target_type="warehouse",
                    target_id=str(q.get("warehouse_id")),
                    recommendation=f"Query {q.get('statement_id')} scans {read_files} files — OPTIMIZE/compact + Z-ORDER on filter cols.",
                    monthly_savings_usd=0.0,  # quantified by storage agent; flagged here as evidence
                    effort="M", risk="Low", confidence=0.6,
                    evidence={"read_files": read_files, "duration_ms": dur},
                    exact_change="OPTIMIZE <table> ZORDER BY (<filter_cols>);",
                    rollback="n/a (idempotent maintenance).",
                ))
            if spilled > _SPILL_BYTES:
                findings.append(Finding(
                    agent=self.name, category="query_spill", target_type="warehouse",
                    target_id=str(q.get("warehouse_id")),
                    recommendation=f"Query {q.get('statement_id')} spills {spilled/1e9:.1f}GB — raise warehouse size or fix shuffle/skew.",
                    monthly_savings_usd=savings_from_runtime(0.0, dur, dur * 0.6),
                    effort="M", risk="Med", confidence=0.5,
                    evidence={"spilled_gb": round(spilled / 1e9, 1)},
                    exact_change="Enable AQE skew handling; or size warehouse up for shorter, cheaper runs.",
                    rollback="Revert warehouse size.",
                ))

        # repeated identical queries -> materialized view / result cache
        for r in ctx.get_facts("repeated_queries"):
            total_ms = float(r.get("total_ms") or 0)
            if total_ms > 600000:  # >10 min cumulative
                findings.append(Finding(
                    agent=self.name, category="repeated_query", target_type="query",
                    target_id=r.get("statement_text", "")[:60],
                    recommendation=f"Query repeated {r.get('exec_count')}x — materialized view / result cache.",
                    monthly_savings_usd=0.0, effort="M", risk="Low", confidence=0.55,
                    evidence={"exec_count": r.get("exec_count"), "total_ms": total_ms},
                    exact_change="CREATE MATERIALIZED VIEW ... ; or enable result cache.",
                    rollback="DROP MATERIALIZED VIEW.",
                ))
        return findings
