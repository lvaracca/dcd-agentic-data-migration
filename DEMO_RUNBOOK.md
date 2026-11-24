# Presenter Live Demo Runbook (45-Minute Choreography)

Copy-paste prompts for **Antigravity** during your live presentation once your Snowflake Trial (`QUICKBITE_PROD`) and GCP prerequisites (`./scripts/01_setup_gcp_prereqs.sh`) are seeded.

---

## Act 1 (00:00 – 05:00) — Live Legacy Stack Tour & Automated Audit
1. **Show briefly on screen**:
   - **Snowsight UI**: Show `QUICKBITE_PROD` (`OPS_RAW` hybrid Iceberg + FDN tables, `IOT_RAW.APP_DELIVERY_PINGS` `VARIANT` JSON, and open **Monitoring -> Task Graph** to show the **7-Node Snowflake Task DAG**).
   - **Airbyte / Power BI**: Show `ingestion-airbyte/airbyte_terraform/main.tf` pointing at Snowflake and `bi-powerbi/.../FCT_PLATFORM_NET_REVENUE.tmdl` using `Snowflake.Databases(...)`.
2. **Prompt Antigravity**:
   ```text
   Audit our live Snowflake QUICKBITE_PROD environment, upstream Airbyte Terraform pipeline, 7-node Snowflake Task DAG, and downstream Power BI (.pbip / TMDL) model. Generate the GCP migration blueprint in gcp-target/MIGRATION_AUDIT_REPORT.md.
   ```

---

## Act 2 (05:00 – 13:00) — Hybrid Data Migration & Seamless Airbyte Cutover
1. **Prompt Antigravity**:
   ```text
   Execute the hybrid Snowflake-to-BigQuery data migration (Zero-Copy BigLake Iceberg for our 4 GCS Iceberg tables + Parquet/native JSON load for the 8 FDN/VARIANT tables), start background Data Profile scans, and re-point our Airbyte Terraform pipeline seamlessly from Snowflake to BigQuery while preserving incremental cursors.
   ```
2. **Optional Live Traffic Injection** (if running local Docker OLTP + Airbyte):
   ```bash
   python3 ingestion-airbyte/simulate_live_orders.py --count 50
   # Trigger Sync in Airbyte UI -> show +50 April 1st orders landing directly in BigQuery!
   ```

---

## Act 3 (13:00 – 26:00) — Snowflake 7-Task Orchestrator -> Dataform DAG (+ Spark & BQ AI)
1. **Prompt Antigravity (Orchestrator Focus)**:
   ```text
   Migrate our 7-node Snowflake Task Graph, Dynamic Table, Views, and Stored Procedure into a BigQuery Dataform repository under gcp-target/dataform/ (preserving exact uppercase Power BI schema contracts), compile and execute the Dataform DAG, and run evals/verify_migration_parity.py to prove 100% mathematical parity.
   ```
   *Show on screen*: Open **BigQuery Studio -> Dataform -> Compiled Graph** side-by-side with Snowsight's Task Graph, then highlight `$153,150.49 == $153,150.49` in the parity check output!

2. **Prompt Antigravity (Snowpark & Cortex Modernization)**:
   ```text
   Migrate our Snowpark fraud-scoring Python job to Google Cloud Managed Spark under gcp-target/spark/ and convert our Snowflake Cortex SQL & ML Forecast scripts to zero-shot BigQuery AI (AI.CLASSIFY, AI.SCORE, and TimesFM AI.FORECAST) under gcp-target/bigquery-ai/, then execute the BigQuery AI queries.
   ```

---

## Act 4 (26:00 – 37:00) — Rescuing Business Logic -> OKF v0.2 & Knowledge Catalog
1. **Prompt Antigravity**:
   ```text
   Extract all undocumented business logic, status code definitions, analytical join traps (SCD2 commissions, Snapshot Trap, refund fan-out, 'CBK-' concat, 3.8.0-beta JSON bug), and KPI formulas from our Snowflake SQL, Snowpark Python, cortex_ops_model.yaml, and Power BI .tmdl DAX measures into Open Knowledge Format (okf/ and bundle/). Then push the table and column descriptions to BigQuery and seed BigQuery query history for Knowledge Catalog Data Insights.
   ```
2. **Optional Remote Context Set Publish** (triggers `@skill:curate-context` 2-gate flow):
   ```text
   Publish our bundle/ context set to Knowledge Catalog in us-central1.
   ```
   *Show on screen*: Open **BigQuery Studio** -> click `DLV_ORD_HDR` and `FCT_PLATFORM_NET_REVENUE` **Schema** (now richly documented!) + **Insights** tab (Usage-based joins!).

---

## Act 5 (37:00 – 45:00) — Seamless Power BI Cutover & Conversational Analytics
1. **Prompt Antigravity (Unplug Snowflake -> Plug into BigQuery in Power BI)**:
   ```text
   Unplug our Power BI Semantic Model in bi-powerbi/ from Snowflake and re-point all table partitions to BigQuery using GoogleBigQuery.Database with the Storage API, keeping 100% of DAX measures and visuals intact, then validate the cutover.
   ```
   *Show on screen*: Commit/sync `.pbip` to Power BI Service (or open in Power BI) -> click **Refresh** -> exact same KPIs (`$153,150.49` Q3 Restaurant Net Revenue) now powered 100% by BigQuery!

2. **Finish in BigQuery Studio (Conversational Analytics)**:
   Ask 2–3 live questions from [conversational_analytics_test_prompts.md](evals/conversational_analytics_test_prompts.md) (e.g., Prompt #01 on Q3 2025 Net Revenue, Prompt #03 on Live Supply Deficit Cities avoiding the Snapshot Trap, and Prompt #04 on EMEA Prime Partners).
