# QuickBite — End-to-End Snowflake-to-GCP Migration Demo (45-Min Format)

Live, zero-downtime migration demo orchestrated by **Antigravity** across the full enterprise data stack:
1. **Upstream Ingestion (`ingestion-airbyte/`)**: PostgreSQL OLTP -> **Airbyte** incremental sync seamlessly re-pointed from `destination-snowflake` to `destination-bigquery` without losing live orders.
2. **Hybrid Storage (`snowflake-source/`)**: **4 Snowflake-Managed Apache Iceberg tables on GCS** (mounted Zero-Copy in BigQuery via **BigLake**) + **8 Native Snowflake FDN / `VARIANT` tables** (migrated to Partitioned/Clustered BigQuery + Native `JSON` + Policy Tags & RLS).
3. **Orchestration & Compute**: **7-Node Snowflake Task DAG** (`AFTER` fan-out/fan-in + `STREAMS` + `DYNAMIC TABLE` + Scripting Stored Proc), **Snowpark Python**, and **Cortex AI/ML** -> migrated to **Dataform (`.sqlx` DAG + assertions)**, **Managed Spark (Dataproc Serverless)**, and **BigQuery AI (TimesFM & Gemini)**.
4. **Business Logic Rescue (`OKF v0.2` -> `Knowledge Catalog`)**: Reverse-engineering undocumented KPIs, status codes, and join traps out of **Snowflake SQL, Snowpark Python, and Power BI DAX (`.tmdl`)** into **BigQuery Metadata**, **Knowledge Catalog (Business Glossary + Context Set + Usage-Based Data Insights)**, and **BigQuery Conversational Analytics**.
5. **Downstream BI Cutover (`bi-powerbi/`)**: Unplugging **Power BI (`QuickBite_Executive_Cockpit.pbip` / TMDL)** from `Snowflake.Databases(...)` and plugging it straight into `GoogleBigQuery.Database(...)` with zero broken visuals.

See [SPECIFICATION.md](SPECIFICATION.md) for the full 45-minute run-of-show and architecture diagrams.

---

## Quickstart: Provision Your Demo Environment (~5 Minutes)

### 1. Create the 30-Day Snowflake Free Trial (`signup.snowflake.com`)
- **Edition**: **`Enterprise`** *(required for Masking & Row Access Policies)*
- **Cloud Provider**: **`Google Cloud Platform (GCP)`**
- **Region**: **`US Central1 (Iowa)` (`us-central1`)** *(co-locates Snowflake, GCS Iceberg, BigLake, Dataform, Knowledge Catalog, and BigQuery AI)*

### 2. Configure `.env` & Python Virtual Environment
```bash
cp .env.example .env
# Fill in GCP_PROJECT_ID and your Snowflake Trial credentials in .env

python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

### 3. Provision GCP Lakehouse Bucket & BigLake Connection (`us-central1`)
```bash
./scripts/01_setup_gcp_prereqs.sh
```

### 4. Seed Snowflake (`624,924` Verified Rows + 7-Node Task DAG + Policies)
Synthetic data files are already generated in `data-generator/output/` (re-run `python3 data-generator/generate_quickbite_data.py` anytime).
```bash
# Step 1: Create Snowflake External Volume & print the 1-line GCS IAM binding command
.venv/bin/python data-generator/seed_snowflake_instance.py --step 1
./scripts/01_setup_gcp_prereqs.sh --grant-snowflake-sa <SNOWFLAKE_GCP_SA_EMAIL>

# Step 2: Create 4 Iceberg + 8 FDN tables, load 624,924 rows, execute the 7-Node Task DAG
#         to populate Gold tables for Power BI, seed QUERY_HISTORY, and suspend Warehouses
.venv/bin/python data-generator/seed_snowflake_instance.py --step 2
```

### 5. Live Airbyte OSS + PostgreSQL OLTP (Hosted on Private GCE VM via IAP)
```bash
# 1. Deploy private GCE VM (quickbite-airbyte-vm) with PostgreSQL OLTP + Airbyte OSS
./scripts/02_deploy_airbyte_vm.sh

# 2. Configure PostgreSQL -> Snowflake (Legacy) & run initial sync
.venv/bin/python ingestion-airbyte/airbyte_cutover_controller.py --action setup-legacy-snowflake

# 3. Open Airbyte Web UI locally in Chrome via IAP Tunnel (http://localhost:8000)
./scripts/open_airbyte_ui_tunnel.sh

# 4. During Act 2 of the demo, cut over Airbyte to BigQuery & inject +50 live orders:
.venv/bin/python ingestion-airbyte/airbyte_cutover_controller.py --action cutover-to-bigquery
.venv/bin/python ingestion-airbyte/simulate_live_orders.py --count 50
.venv/bin/python ingestion-airbyte/airbyte_cutover_controller.py --action trigger-sync
```
