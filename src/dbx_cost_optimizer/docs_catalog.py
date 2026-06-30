"""Maps finding categories -> official Databricks documentation.

The PDF agent dispatches on `Finding.category` to attach the right doc link +
a short "how it works" note. Extend by adding entries; unknown categories fall
back to a docs search URL so a link is always present.

URLs point at docs.databricks.com (AWS path; Azure/GCP mirror the same slugs).
Verify against your cloud — Databricks occasionally reorganizes doc slugs.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class DocEntry:
    fix_family: str          # grouping bucket in the PDF
    title: str               # doc page title
    url: str                 # official doc link
    how_it_works: str        # 1-2 lines explaining the mechanism


def _search(q: str) -> str:
    return f"https://docs.databricks.com/en/search.html?q={q.replace(' ', '+')}"


CATALOG: Dict[str, DocEntry] = {
    "cluster_lower_max_workers": DocEntry(
        "Compute right-sizing",
        "Compute configuration best practices — autoscaling",
        "https://docs.databricks.com/aws/en/compute/cluster-config-best-practices",
        "Autoscaling adds/removes workers to match load. Lowering the max ceiling caps spend "
        "on chronically idle clusters; a floor of 1 lets it scale from minimal.",
    ),
    "cluster_downsize": DocEntry(
        "Compute right-sizing",
        "Compute configuration best practices — instance types",
        "https://docs.databricks.com/aws/en/compute/cluster-config-best-practices",
        "DBU cost scales with node size/family. Stepping a worker type down one tier cuts "
        "DBU/hr when CPU and memory headroom are consistently unused.",
    ),
    "no_autoterminate": DocEntry(
        "Compute right-sizing",
        "Manage compute — automatic termination",
        "https://docs.databricks.com/aws/en/compute/clusters-manage",
        "Auto-termination shuts an idle cluster after N minutes of inactivity, so you stop "
        "paying for an interactive cluster left running overnight.",
    ),
    "wrong_cluster_type": DocEntry(
        "Job configuration",
        "Use compute for jobs (job vs all-purpose)",
        "https://docs.databricks.com/aws/en/jobs/compute",
        "Jobs compute bills at a lower DBU rate than all-purpose. A scheduled job should run "
        "on an ephemeral job cluster, not a shared interactive one.",
    ),
    "failed_run_waste": DocEntry(
        "Job configuration",
        "Configure job retries and failure handling",
        "https://docs.databricks.com/aws/en/jobs/settings",
        "Repeated failed/retried runs burn DBU for no output. Cap retries and fix the "
        "termination cause to stop paying for doomed runs.",
    ),
    "batch_eligible": DocEntry(
        "Job configuration",
        "File arrival triggers",
        "https://docs.databricks.com/aws/en/jobs/file-arrival-triggers",
        "Many tiny scheduled runs pay cluster startup repeatedly. Trigger on data arrival or "
        "batch into coarser intervals to amortize startup.",
    ),
    "small_files_scan": DocEntry(
        "Storage maintenance",
        "OPTIMIZE and file compaction",
        "https://docs.databricks.com/aws/en/delta/optimize",
        "Many small files inflate scan time/cost. OPTIMIZE compacts them into right-sized "
        "files; fewer files = less I/O per query.",
    ),
    "needs_optimize": DocEntry(
        "Storage maintenance",
        "Predictive optimization & liquid clustering",
        "https://docs.databricks.com/aws/en/optimizations/predictive-optimization",
        "Predictive optimization auto-runs OPTIMIZE/VACUUM. Liquid clustering replaces "
        "partitioning/Z-ORDER for skipping data on high-cardinality filters.",
    ),
    "query_spill": DocEntry(
        "Query tuning",
        "Adaptive query execution (AQE)",
        "https://docs.databricks.com/aws/en/optimizations/aqe",
        "Disk spill means shuffles exceed memory, often from skew. AQE dynamically handles "
        "skew and coalesces partitions; right-sizing the warehouse also shortens runs.",
    ),
    "repeated_query": DocEntry(
        "Query tuning",
        "Materialized views",
        "https://docs.databricks.com/aws/en/views/materialized",
        "An identical heavy query run repeatedly recomputes every time. A materialized view "
        "precomputes and incrementally refreshes the result.",
    ),
}

_DEFAULT_FAMILY = "Other"


def lookup(category: str) -> DocEntry:
    if category in CATALOG:
        return CATALOG[category]
    return DocEntry(
        _DEFAULT_FAMILY,
        f"Databricks docs — {category}",
        _search(category.replace("_", " ")),
        "No dedicated mapping yet; link points at official docs search.",
    )
