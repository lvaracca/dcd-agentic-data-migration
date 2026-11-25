# UrbanFork Snowflake-to-GCP Migration Demo — Workspace Agent Rules

## Environment & Tooling Rules
- Read `agent-config.json` and `.env` (never print secrets or passwords in chat output) to resolve `GCP_PROJECT_ID`, `GCP_REGION` (`us-central1`), `GCS_LAKEHOUSE_BUCKET`, BigQuery datasets, and Snowflake connection details.
- Always execute Python scripts using `.venv/bin/python` (never install packages globally; see `requirements.txt`).
- Keep all generated code, SQL comments, Dataform models, Open Knowledge Format (`okf/` and `bundle/`) files, Knowledge Catalog glossary terms, and Tableau (`.twb`) artifacts strictly in **English**.
- When running `bq` or `gcloud` CLI commands, follow `@skill:enforcing-resource-attribution` (`--label datacloud:antigravity` on supported `bq` commands and `CLOUDSDK_METRICS_ENVIRONMENT` on `gcloud` commands).

## Demo Workflow Mapping (5-Act Agentic Migration)
- **Act 1 (Live Audit)**: Use skill `snowflake-live-audit` to inspect the live Snowflake `URBANFORK_PROD` instance, Airbyte config, 7-node Snowflake Task DAG, and Tableau Cloud (`.twb`) dependencies.
- **Act 2 (Hybrid Data Migration)**: Use skill `snowflake-hybrid-data-cutover` to mount the 4 GCS Iceberg tables zero-copy via BigLake and migrate the 8 Native Snowflake / `VARIANT` tables to BigQuery (`JSON` + Policy Tags/RLS) while production Snowflake stays live in parallel.
- **Act 3 (Orchestrator, Spark & AI)**:
  - Use skill `snowflake-tasks-to-dataform` (alongside `@skill:dataform-bigquery`) to convert the 7-node Snowflake Task Graph (`03_streams_tasks_dynamic_tables.sql`) into a compiled & tested Dataform DAG under `gcp-target/dataform/`, then verify cent-level parity with `evals/verify_migration_parity.py`.
  - Use skill `snowpark-and-cortex-migrator` (alongside `@skill:gcp-spark` and `@skill:bigquery-ai-ml`) to migrate Snowpark Python to Managed Spark and Cortex SQL to zero-shot BigQuery AI (`AI.CLASSIFY`, `AI.SCORE`, `AI.FORECAST`).
- **Act 4 (Centralize Business KPIs -> OKF -> Knowledge Catalog)**: Use skill `extract-business-logic-to-okf` (and `@skill:curate-context` when publishing to a remote Knowledge Catalog Context Set) to consolidate distributed business logic (KPIs, status codes, and join rules) from Snowflake SQL, Snowpark Python, and Tableau Calculated Fields into `okf/` and `bundle/`, enrich BigQuery descriptions, and populate Knowledge Catalog Business Glossary & `QUERY_HISTORY`.
- **Act 5 (Final Cutover, BI & AI Q&A)**: Use skill `repoint-tableau-to-bigquery` to switch `bi-tableau/` workbooks (`.twb`) from Snowflake to BigQuery, validate 100% schema/Calculated Field compatibility and grounded Conversational Analytics, then switch `ingestion-airbyte/airbyte_terraform/main.tf` from Snowflake to BigQuery (Keyless ADC) and suspend legacy Snowflake warehouses.
