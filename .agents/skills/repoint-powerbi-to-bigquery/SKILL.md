---
name: repoint-powerbi-to-bigquery
description: >-
  Unplugs the QuickBite Power BI Project (.pbip / TMDL semantic model) from
  Snowflake (Snowflake.Databases) and seamlessly re-points all M-query table
  partitions to Google BigQuery (GoogleBigQuery.Database with Storage API),
  validating 100% column and DAX measure compatibility. Use during Act 5.
---

# Seamless Power BI Cutover: Unplug Snowflake -> Plug into BigQuery (Act 5)

## Procedure

1. **Update Connection Parameters (`expressions.tmdl` & `model.tmdl`)**:
   In `bi-powerbi/QuickBite_Executive_Cockpit.SemanticModel/definition/expressions.tmdl` and `model.tmdl`:
   - Replace `SnowflakeHost`, `SnowflakeWarehouse`, and `SnowflakeDatabase` with `GcpProjectId` (`"<GCP_PROJECT_ID>"` from `.env` / `agent-config.json`) and `BigQueryDataset` (`"quickbite_gold_mart"`).

2. **Re-Point M-Query Partitions Across All 3 Gold Tables**:
   Update the `partition ... = m` block in each of:
   - `tables/FCT_PLATFORM_NET_REVENUE.tmdl`
   - `tables/DIM_PRIME_PARTNER_SCORECARD.tmdl`
   - `tables/DT_LIVE_ZONE_SUPPLY_DEFICIT.tmdl`

   Replace the `Snowflake.Databases(...)` expression with BigQuery's Storage API connector:
   ```powerquery
   let
       Source = GoogleBigQuery.Database([BillingProject=GcpProjectId, UseStorageApi=true]),
       Project = Source{[Name=GcpProjectId]}[Data],
       MartDataset = Project{[Name=BigQueryDataset,Kind="Schema"]}[Data],
       Tbl = MartDataset{[Name="<TABLE_NAME>",Kind="Table"]}[Data]
   in
       Tbl
   ```
   **Do NOT alter any DAX `measure` formulas, `column` names, or `report.json` visuals!** Preserving 100% of DAX and report bindings proves a zero-rewrite BI cutover.

3. **Run Automated TMDL-to-BigQuery Contract Verification**:
   Execute [validate_tmdl_cutover.py](./scripts/validate_tmdl_cutover.py):
   ```bash
   .venv/bin/python .agents/skills/repoint-powerbi-to-bigquery/scripts/validate_tmdl_cutover.py
   ```
   Confirm `0` remaining `Snowflake.Databases` references and `100%` column match against live BigQuery `INFORMATION_SCHEMA.COLUMNS`.
