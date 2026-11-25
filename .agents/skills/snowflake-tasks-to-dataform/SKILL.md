---
name: snowflake-tasks-to-dataform
description: >-
  Converts the UrbanFork 7-Node Snowflake Task Orchestration DAG, CDC Streams,
  Dynamic Table, Views, and Snowflake Scripting Stored Procedure into an
  idiomatic Google Cloud Dataform (.sqlx) repository on BigQuery, compiles and
  executes the DAG, and runs cent-level parity verification. Use during Act 3
  when migrating Snowflake Tasks and SQL pipelines to Dataform.
---

# Snowflake 7-Task Orchestration DAG -> BigQuery Dataform Migration (Act 3A)

Load `@skill:dataform-bigquery` alongside this skill for Dataform CLI best practices.

## Critical Schema Contract Rule (For Seamless Power BI Cutover!)
Power BI's Power Query (`M`) engine is **case-sensitive** on table and column names!
When generating the Dataform Gold Marts in `urbanfork_gold_mart`, preserve **EXACT UPPERCASE** table names (`name: "FCT_PLATFORM_NET_REVENUE"`, `name: "DIM_PRIME_PARTNER_SCORECARD"`, `name: "DT_LIVE_ZONE_SUPPLY_DEFICIT"`, `name: "RPT_PBI_EXECUTIVE_SUMMARY"`) and **UPPERCASE column aliases** matching `snowflake-source/03_streams_tasks_dynamic_tables.sql` so Power BI re-points with zero broken visuals.

## Step-by-Step Translation Mapping (`gcp-target/dataform/`)

Read `snowflake-source/03_streams_tasks_dynamic_tables.sql` and `snowflake-source/04_legacy_views_and_procs.sql`, then scaffold `gcp-target/dataform/`:

1. **`workflow_settings.yaml`**:
   - Set `defaultProject: <GCP_PROJECT_ID>`, `defaultLocation: us-central1`, `defaultDataset: urbanfork_gold_mart`, `defaultAssertionDataset: urbanfork_gold_mart_assertions`.
2. **Source Declarations (`definitions/sources/raw_sources.js` or `.sqlx`)**:
   - Declare the 11 tables in `urbanfork_raw_ops` and `APP_DELIVERY_PINGS` in `urbanfork_raw_iot`.
3. **Map Each of the 7 Snowflake Tasks + Dynamic Table to Dataform Nodes**:
   - `TSK_01A_STAGE_ORDERS` -> `definitions/staging/STG_ORDER_BASKETS.sqlx` (`type: "table"`, `partitionBy: "ORD_DT"`, `assertions: { uniqueKey: ["ORD_ID"], nonNull: ["ORD_ID", "GMV_USD"] }`).
   - `TSK_01B_PARSE_PINGS` -> `definitions/staging/STG_CLEAN_DELIVERY_PINGS.sqlx`:
     - Convert Snowflake `VARIANT` syntax (`p.PAYLOAD:app_ver::VARCHAR`, `TRY_TO_NUMBER(p.PAYLOAD:metrics.prep_sec::VARCHAR)`, `ARRAY_CONTAINS('SLA_EXCEEDED'::VARIANT, p.PAYLOAD:anomaly_flags)`) to BigQuery native **`JSON`**:
       - `LAX_STRING(p.PAYLOAD.app_ver)`
       - `LAX_INT64(p.PAYLOAD.metrics.prep_sec)`
       - `'SLA_EXCEEDED' IN UNNEST(JSON_VALUE_ARRAY(p.PAYLOAD.anomaly_flags))`
     - Keep `WHERE LAX_STRING(p.PAYLOAD.stage) = 'DELIVERED' AND LAX_STRING(p.PAYLOAD.app_ver) != '3.8.0-beta'` and `QUALIFY ROW_NUMBER() OVER (...) = 1`.
   - `TSK_01C_STAGE_DISPUTES` -> `definitions/staging/STG_ORDER_DISPUTES_AGG.sqlx` (convert `COUNT_IF(...)` -> `COUNTIF(...)`, `ZEROIFNULL(x)` -> `COALESCE(x, 0)`, keep `CONCAT('CBK-', d.ORD_ID) = led.REF_DOC_TXT`).
   - `TSK_02A_MART_NET_REVENUE` -> `definitions/marts/FCT_PLATFORM_NET_REVENUE.sqlx` (`type: "table"`, `partitionBy: "CAL_DT"`, `clusterBy: ["REG_CD", "VERT_CD"]`, `assertions: { nonNull: ["CAL_DT", "PLATFORM_NET_REVENUE_USD"] }`; convert `IFF(a,b,c)` -> `IF(a,b,c)` and `ROUND(CAST(... AS NUMERIC), 2)`).
   - `TSK_02B_MART_PRIME_PARTNERS` -> `definitions/marts/DIM_PRIME_PARTNER_SCORECARD.sqlx` (`DATEADD('day', -90, a.MAX_DT)` -> `DATE_SUB(a.MAX_DT, INTERVAL 90 DAY)`).
   - `DT_LIVE_ZONE_SUPPLY_DEFICIT` -> `definitions/marts/DT_LIVE_ZONE_SUPPLY_DEFICIT.sqlx` (`QUALIFY RANK() OVER (PARTITION BY s.ZONE_ID ORDER BY s.SNAP_TS DESC) = 1`).
   - `SP_AUDIT_DISPUTE_CHARGEBACKS` + `TSK_03_REFRESH_PBI_AND_AUDIT` -> `definitions/marts/RPT_PBI_EXECUTIVE_SUMMARY.sqlx` + `definitions/operations/sp_audit_dispute_chargebacks.sqlx` (`type: "operations"`, `dependencies: ["RPT_PBI_EXECUTIVE_SUMMARY"]`).
   - Also translate `MART.VW_DELIVERY_SLA_TELEMETRY` (`ASOF JOIN` -> deterministic `LEFT JOIN` with `QUALIFY ROW_NUMBER() OVER (PARTITION BY h.ORD_ID ORDER BY d.DSP_TS ASC) = 1` where `lp.DELIVERED_PING_TS <= d.DSP_TS`).

## Validation & Execution
1. Run `dataform compile gcp-target/dataform` until 0 compilation errors.
2. Run `dataform run gcp-target/dataform` (or execute compiled DDL via `bq query --label=datacloud:antigravity` if `dataform` CLI credentials need `.df-credentials.json`).
3. Run the automated parity check:
   ```bash
   .venv/bin/python evals/verify_migration_parity.py
   ```
