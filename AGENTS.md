# UrbanFork Snowflake-to-GCP Migration Demo — Workspace Agent Rules

## Environment & Tooling Rules
- Read `agent-config.json` and `.env` (never print secrets or passwords in chat output) to resolve `GCP_PROJECT_ID`, `GCP_REGION` (`us-central1`), `GCS_LAKEHOUSE_BUCKET`, BigQuery datasets, and Snowflake connection details.
- Always execute Python scripts using `.venv/bin/python` (never install packages globally; see `requirements.txt`).
- Keep all generated code, SQL comments, Dataform models, Open Knowledge Format (`okf/` and `bundle/`) files, Knowledge Catalog glossary terms, and Power BI `.tmdl` artifacts strictly in **English**.
- When running `bq` or `gcloud` CLI commands, follow `@skill:enforcing-resource-attribution` (`--label datacloud:antigravity` on supported `bq` commands and `CLOUDSDK_METRICS_ENVIRONMENT` on `gcloud` commands).

## Demo Workflow Mapping (45-Minute Run-of-Show)
- **Act 1 (Audit)**: Use skill `snowflake-live-audit` to inspect the live Snowflake `URBANFORK_PROD` instance, Airbyte config, 7-node Snowflake Task DAG, and Power BI `.pbip` dependencies.
- **Act 2 (Data & Airbyte Cutover)**: Use skill `snowflake-hybrid-data-cutover` to mount the 4 GCS Iceberg tables via BigLake, migrate the 8 Native/`VARIANT` tables to BigQuery (`JSON` + Policy Tags/RLS), and switch `ingestion-airbyte/airbyte_terraform/main.tf` from Snowflake to BigQuery.
- **Act 3 (Orchestrator, Spark & AI)**:
  - Use skill `snowflake-tasks-to-dataform` (alongside `@skill:dataform-bigquery`) to convert the 7-node Snowflake Task Graph (`03_streams_tasks_dynamic_tables.sql`) into a compiled & tested Dataform DAG under `gcp-target/dataform/`, then verify cent-level parity with `evals/verify_migration_parity.py`.
  - Use skill `snowpark-and-cortex-migrator` (alongside `@skill:gcp-spark` and `@skill:bigquery-ai-ml`) to migrate Snowpark Python to Managed Spark and Cortex SQL to zero-shot BigQuery AI (`AI.CLASSIFY`, `AI.SCORE`, `AI.FORECAST`).
- **Act 4 (Business Logic -> OKF -> Knowledge Catalog)**: Use skill `extract-business-logic-to-okf` (and `@skill:curate-context` when publishing to a remote Knowledge Catalog Context Set) to extract KPIs, status codes, and join caveats from Snowflake SQL, Snowpark Python, and Power BI DAX into `okf/` and `bundle/`, enrich BigQuery descriptions, and seed `QUERY_HISTORY` for Usage-Based Data Insights.
- **Act 5 (Power BI Re-Pointing)**: Use skill `repoint-powerbi-to-bigquery` to switch `bi-powerbi/` `.tmdl` partitions from `Snowflake.Databases(...)` to `GoogleBigQuery.Database(...)` and validate 100% schema/DAX compatibility.
