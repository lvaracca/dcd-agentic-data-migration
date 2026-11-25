---
name: snowflake-live-audit
description: >-
  Audits the live Snowflake URBANFORK_PROD instance, upstream Airbyte Terraform
  ingestion config, 7-node Snowflake Task Graph, governance policies, and
  downstream Tableau (.twb) workbooks to produce an end-to-end GCP migration
  blueprint. Use during Act 1 when asked to inspect, discover, or audit the
  Snowflake environment before migration.
---

# Snowflake Live End-to-End Stack Audit (Act 1)

## Procedure

1. **Run the Live Snowflake Discovery Helper**:
   Execute [inspect_snowflake_estate.py](./scripts/inspect_snowflake_estate.py) using `.venv/bin/python`:
   ```bash
   .venv/bin/python .agents/skills/snowflake-live-audit/scripts/inspect_snowflake_estate.py
   ```
   *(If live Snowflake connectivity is unavailable, inspect `snowflake-source/*.sql` and `data-generator/output/ground_truth_manifest.json` directly and note that static source analysis was used.)*

2. **Inspect Upstream Ingestion & Downstream BI**:
   - Read `ingestion-airbyte/airbyte_terraform/main.tf` to identify active incremental streams (`dlv_ord_hdr`, `dlv_ord_item_ln`, `dsp_refund_fct`) and cursor fields (`updated_at`).
   - Read `bi-tableau/UrbanFork_Executive_Cockpit_Snowflake.twb` to list every Snowflake `MART` table, bound column, and Tableau Calculated Field consumed by the executive dashboard.

3. **Generate Migration Blueprint**:
   Write `gcp-target/MIGRATION_AUDIT_REPORT.md` summarizing:
   - **Hybrid Table Strategy**: Which 4 tables are Snowflake-Managed Iceberg on GCS (eligible for Zero-Copy BigLake mount) vs. 8 Native Snowflake tables (including `IOT_RAW.APP_DELIVERY_PINGS` `VARIANT` -> BigQuery `JSON`).
   - **Orchestrator Graph**: Visual Mermaid diagram of the **7-Node Snowflake Task DAG** (`TSK_00` -> `TSK_01A/B/C` -> `TSK_02A/B` -> `TSK_03`) + `DT_LIVE_ZONE_SUPPLY_DEFICIT` mapped 1-to-1 to BigQuery Dataform `.sqlx` targets.
   - **Governance & Distributed Business Logic Inventory**: Masking/RLS policies detected + KPIs and join rules distributed across SQL, Snowpark, and Tableau (`Platform Net Revenue`, `Prime Partner`, `SCD2 Commission`, `Snapshot Trap`, `'CBK-' || ORD_ID`).
   - **Recommended BigQuery Partitioning & Clustering** per table.
