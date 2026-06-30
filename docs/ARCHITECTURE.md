# High-Level Architecture

```mermaid
flowchart TD
    subgraph AUTH[Auth & Config]
      CFG["~/.databrickscfg profile\n(Databricks CLI)"]
      ENV[".env / env vars"]
    end

    subgraph SRC[Data Sources]
      ST["System Tables\n(billing, compute, lakeflow, query.history)"]
    end

    subgraph CONN[Connector layer]
      MOCK[MockConnector]
      SQLC[DatabricksSQLConnector]
      SPK["SparkConnector\n(in-workspace job)"]
    end

    subgraph ORCH[Orchestrator — supervisor]
      direction TB
      T0["tier0: telemetry\n(runs SQL → facts)"]
      T1A[tier1: compute]
      T1B[tier1: job_query]
      T1C[tier1: storage]
      T2A[tier2: forecast]
      T2B[tier2: report]
      T2C[tier2: pdf_report]
      T2D["tier2: sink\n(Delta tables)"]
      T3[tier3: alert]
    end

    CS[(ContextStore\nfacts + findings + meta)]
    TOOLS["tools/\nrightsizing · savings"]
    SKILLS["skills/\nplaybook cards"]
    DOCS["docs_catalog\nofficial doc links"]

    subgraph DELIVER[Delivery]
      EMAIL[[Email alert\nrecipient list]]
      PDF[[PDF report\n+ docs links]]
      TBL[(Delta:\ncost_findings\ncost_usage_daily)]
      DASH[[AI/BI Dashboard\nLakeview]]
      GENIE[[Genie\ninteractive Q&A]]
    end

    CFG --> CONN
    ENV --> CONN
    ST --> SQLC
    ST --> SPK
    CONN --> T0
    T0 --> CS
    CS --> T1A & T1B & T1C
    T1A & T1B & T1C --> CS
    TOOLS -. numbers .-> T1A & T1B & T1C
    SKILLS -. playbooks .-> T1A & T1B & T1C
    CS --> T2A & T2B & T2C & T2D
    DOCS -. links .-> T2C
    T2D --> TBL
    CS --> T3
    T3 --> EMAIL
    T2C --> PDF
    TBL --> DASH
    TBL --> GENIE
    GENIE <-->|chat| USER((User))
```

## Layers

| Layer | Responsibility | Swap point |
|-------|----------------|-----------|
| Auth/Config | `Settings`, `~/.databrickscfg` profile | `databricks_cfg.read_profile` |
| Connector | run SQL (mock / SQL warehouse / Spark) | `connectors/base.Connector` |
| Telemetry | System Tables → normalized facts | `sql/queries.py` |
| Analysis agents | detect waste, emit `Finding`s | `@register_agent` |
| Tools | deterministic $ math | `tools/` |
| Skills | capability playbooks | `skills/*.md` |
| Delivery | email · PDF · Delta · dashboard · Genie | `notifications/`, agents |

## Run modes
- **Local / CI** — `dbxopt run` (env or CLI profile auth; SQL warehouse connector).
- **In-workspace job (DAB)** — `databricks bundle run` → Spark connector, writes Delta, dashboard resource renders.
- **Interactive** — `dbxopt genie` chats over the output tables.
```
