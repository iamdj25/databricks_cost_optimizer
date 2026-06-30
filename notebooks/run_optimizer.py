# Databricks notebook source
# MAGIC %md
# MAGIC # Databricks Cost Optimizer — job notebook
# MAGIC Runs the multi-agent optimizer on this workspace using the cluster's own
# MAGIC permissions (Spark connector over System Tables), writes findings to Delta,
# MAGIC and (optionally) creates the AI/BI dashboard.

# COMMAND ----------
# MAGIC %pip install dbx-cost-optimizer[pdf]
# MAGIC dbutils.library.restartPython()

# COMMAND ----------
dbutils.widgets.text("catalog", "main")
dbutils.widgets.text("schema", "cost_optimizer")
dbutils.widgets.text("warehouse_id", "")

import os
os.environ["DBX_CATALOG"] = dbutils.widgets.get("catalog")
os.environ["DBX_SCHEMA"] = dbutils.widgets.get("schema")
os.environ["DBX_WAREHOUSE_ID"] = dbutils.widgets.get("warehouse_id")

# COMMAND ----------
from dbx_cost_optimizer import Orchestrator, Settings

# in-workspace -> build_connector auto-selects the Spark connector
orch = Orchestrator(Settings.load())
orch.alert_send_email = False
ctx = orch.run()

print("identified savings $/mo:", ctx.total_identified_savings())
print("findings table:", ctx.meta.get("sink_findings_table"))
display(spark.table(ctx.meta["sink_findings_table"]))

# COMMAND ----------
# MAGIC %md Optional: create the dashboard programmatically (or use the DAB dashboard resource).
# COMMAND ----------
from dbx_cost_optimizer.agents.dashboard import DashboardAgent
DashboardAgent(Settings.load(), orch.connector).run(ctx)
print("dashboard:", ctx.meta.get("dashboard_url") or ctx.meta.get("dashboard_error"))
