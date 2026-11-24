---
name: snowflake-hybrid-data-cutover
description: >-
  Executes the Act 2 hybrid data migration from Snowflake QUICKBITE_PROD to
  Google BigQuery (Zero-Copy BigLake Iceberg mount for the 4 GCS Iceberg tables
  + Parquet/NDJSON unload for the 8 Native FDN/VARIANT tables + BigQuery RLS &
  Policy Tags) and seamlessly switches the Airbyte Terraform destination from
  Snowflake to BigQuery. Use when asked to migrate the Snowflake data or
  re-point Airbyte ingestion.
---

# Hybrid Snowflake-to-BigQuery Data Migration & Airbyte Cutover (Act 2)

## Procedure

1. **Execute Hybrid Data & BigLake Iceberg Migration**:
   Run [migrate_hybrid_tables_to_bq.py](./scripts/migrate_hybrid_tables_to_bq.py) via `.venv/bin/python`:
   ```bash
   .venv/bin/python .agents/skills/snowflake-hybrid-data-cutover/scripts/migrate_hybrid_tables_to_bq.py
   ```
   What this script automates:
   - Queries Snowflake `SYSTEM$GET_ICEBERG_TABLE_INFORMATION(...)` for `DLV_ORD_HDR`, `DLV_ORD_ITEM_LN`, `ZNE_FLEET_SNAP`, and `MRC_PAYOUT_LEDGER`, mounts them **Zero-Copy** as BigLake Iceberg tables (`*_iceberg_ext`) in `quickbite_raw_ops` (< 3 seconds), and creates partitioned/clustered BigQuery operational tables ready to accept live incremental Airbyte writes!
   - Unloads the 8 Native Snowflake FDN tables (`COPY INTO @OPS_RAW.GCS_EXPORT_STAGE/...`) to GCS and loads them into `quickbite_raw_ops` and `quickbite_raw_iot` (landing `APP_DELIVERY_PINGS.PAYLOAD` into BigQuery's native **`JSON`** column!).
   - Creates `gcp-target/security/bigquery_rls_and_masking.sql` and applies the regional Row Access Policy on `GEO_ZONE_LKP`.

2. **Start Background Knowledge Catalog Data Profile Scans Early**:
   Kick off asynchronous Data Profile scans in the background (`--async`) on the migrated tables so they complete naturally while Act 3 runs!

3. **Seamless Airbyte Cutover (`destination-snowflake` -> `destination-bigquery`)**:
   - Edit `ingestion-airbyte/airbyte_terraform/main.tf` to switch `destination_id` from Snowflake to BigQuery (preserving `incremental_deduped_history` and `cursor_field = ["updated_at"]`).
   - AND execute the live Airbyte OSS cutover against `quickbite-airbyte-vm` so the live Airbyte UI switches from Snowflake (`inactive`) to BigQuery (`active`):
     ```bash
     .venv/bin/python ingestion-airbyte/airbyte_cutover_controller.py --action cutover-to-bigquery
     ```

4. **Verification**:
   Confirm row counts across all 12 tables in BigQuery match `data-generator/output/ground_truth_manifest.json` (`624,924` total rows).
