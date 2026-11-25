---
name: repoint-tableau-to-bigquery
description: >-
  Unplugs the UrbanFork Tableau Cloud workbooks (.twb) from Snowflake and
  seamlessly re-points connections to Google BigQuery (OAuth, google-sql
  dialect) while validating 100% column and Calculated Field compatibility,
  followed by Airbyte live cutover and legacy Snowflake warehouse suspension.
  Use during Act 5.
---

# Seamless Tableau Cloud Cutover & Final Airbyte Switch (Act 5)

## Procedure

1. **Re-Point Tableau Workbook XML (`bi-tableau/`)**:
   Run [repoint_twb_to_bigquery.py](../../../bi-tableau/repoint_twb_to_bigquery.py) via `.venv/bin/python`:
   ```bash
   .venv/bin/python bi-tableau/repoint_twb_to_bigquery.py \
     --input bi-tableau/UrbanFork_Executive_Cockpit_Snowflake.twb \
     --output bi-tableau/UrbanFork_Executive_Cockpit_BigQuery.twb
   ```
   - Replaces `<connection class='snowflake'>` with `<connection class='bigquery' authentication='oauth' project='dcd-migration-demo' schema='urbanfork_gold_mart' connection-dialect='google-sql'>`.
   - Updates table relation `[MART].[FCT_PLATFORM_NET_REVENUE]` -> `[urbanfork_gold_mart].[FCT_PLATFORM_NET_REVENUE]`.
   - Preserves 100% of uppercase column bindings, 4 executive Calculated Fields (`Q3 2025 Restaurant Net Revenue ($)`, `FY25 Restaurant Net Revenue ($)`, `Effective Take-Rate %`, `Approved Refund Ratio %`), and dashboard layouts.

2. **Validate 100% Schema & Calculated Field Compatibility**:
   Run [validate_twb_cutover.py](./scripts/validate_twb_cutover.py) via `.venv/bin/python`:
   ```bash
   .venv/bin/python .agents/skills/repoint-tableau-to-bigquery/scripts/validate_twb_cutover.py
   ```
   Confirms zero legacy Snowflake connections remain and every bound column exists in live BigQuery `dcd-migration-demo.urbanfork_gold_mart.FCT_PLATFORM_NET_REVENUE`.

3. **Tableau Cloud UI Switch & Grounded Conversational Analytics**:
   - In Tableau Cloud: **Data -> Replace Data Source** (`UrbanFork_Net_Revenue_Snowflake` -> `UrbanFork_Net_Revenue_BigQuery`) or upload `bi-tableau/UrbanFork_Executive_Cockpit_BigQuery.twb` via Google OAuth (`0` broken charts, exact `$153,150.49` Q3 benchmark).
   - Verify BigQuery Conversational Analytics Q&A grounded in Knowledge Catalog (`urbanfork-enterprise-glossary` & OKF `bundle/`).

4. **Final Airbyte Cutover & Suspend Snowflake**:
   - Switch Airbyte destination (`ingestion-airbyte/airbyte_terraform/main.tf`) from Snowflake to BigQuery (Keyless ADC), verify live CDC sync, and suspend legacy Snowflake warehouses (`UF_LOAD_WH`, `UF_TRANSFORM_WH`).
