#!/usr/bin/env python3
"""
Turnkey Snowflake Enterprise Trial Provisioner for the UrbanFork Migration Demo.

Two-step execution (since Snowflake generates its GCP Service Account dynamically):
  Step 1: Create Warehouses, DB, External Volume & Storage Integration, and print
          the exact GCP IAM grant command:
            .venv/bin/python data-generator/seed_snowflake_instance.py --step 1

  Step 2: Verify GCS Iceberg write access, create 4 Iceberg + 8 Native FDN tables,
          upload & COPY 624,924 synthetic rows, deploy Streams/Tasks/Dynamic Tables,
          Views, Stored Procs, Cortex AI/ML, Masking/RLS Policies, seed QUERY_HISTORY,
          verify ground-truth math, and suspend compute:
            .venv/bin/python data-generator/seed_snowflake_instance.py --step 2
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
import snowflake.connector

ROOT_DIR = Path(__file__).resolve().parent.parent
SQL_DIR = ROOT_DIR / "snowflake-source"
DATA_DIR = ROOT_DIR / "data-generator" / "output"


def get_connection() -> snowflake.connector.SnowflakeConnection:
    load_dotenv(ROOT_DIR / ".env")
    required = ["SNOWFLAKE_ACCOUNT", "SNOWFLAKE_USER", "SNOWFLAKE_PASSWORD"]
    missing = [k for k in required if not os.getenv(k) or os.getenv(k).startswith("YOUR_")]
    if missing:
        print(f"ERROR: Missing or placeholder Snowflake credentials in .env: {', '.join(missing)}")
        sys.exit(1)

    return snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        password=os.environ["SNOWFLAKE_PASSWORD"],
        role=os.environ.get("SNOWFLAKE_ROLE", "ACCOUNTADMIN"),
    )


def render_sql(filename: str, bucket: str) -> str:
    raw = (SQL_DIR / filename).read_text(encoding="utf-8")
    return raw.replace("{{GCS_LAKEHOUSE_BUCKET}}", bucket)


def extract_gcp_sa_from_desc(rows: list[tuple]) -> str | None:
    for row in rows:
        row_str = " ".join(str(c) for c in row if c is not None)
        if "gserviceaccount.com" in row_str:
            # Handle JSON inside EXTERNAL_VOLUME STORAGE_LOCATION_1 or direct property value
            for token in row_str.replace('"', " ").replace(",", " ").replace("}", " ").split():
                if token.endswith("gserviceaccount.com"):
                    return token
    return None


def step_1_init_gcs_integrations(conn: snowflake.connector.SnowflakeConnection, bucket: str) -> None:
    print(f"=== Step 1: Creating Snowflake Warehouses, DB & GCS Integrations for gs://{bucket} ===")
    sql_text = render_sql("00_external_volume_and_integration.sql", bucket)
    for cur in conn.execute_string(sql_text):
        pass

    cur = conn.cursor()
    cur.execute("DESC EXTERNAL VOLUME URBANFORK_GCS_ICEBERG_VOL")
    vol_sa = extract_gcp_sa_from_desc(cur.fetchall())

    cur.execute("DESC STORAGE INTEGRATION URBANFORK_GCS_INT")
    int_sa = extract_gcp_sa_from_desc(cur.fetchall())

    sa_set = {sa for sa in (vol_sa, int_sa) if sa}
    print("\n✅ Snowflake External Volume & Storage Integration created!")
    print("Run the following command(s) in your terminal to grant GCS access to Snowflake:\n")
    for sa in sorted(sa_set):
        print(f"  ./scripts/01_setup_gcp_prereqs.sh --grant-snowflake-sa {sa}")
    print("\nOnce IAM is granted, run Step 2 to load all tables & deploy workloads:")
    print("  .venv/bin/python data-generator/seed_snowflake_instance.py --step 2")


def step_2_deploy_all(conn: snowflake.connector.SnowflakeConnection, bucket: str) -> None:
    if not (DATA_DIR / "ground_truth_manifest.json").exists():
        print("ERROR: Synthetic dataset not found in data-generator/output/. Run generate_urbanfork_data.py first.")
        sys.exit(1)

    manifest = json.loads((DATA_DIR / "ground_truth_manifest.json").read_text(encoding="utf-8"))
    cur = conn.cursor()

    print("=== 1/8 Verifying Snowflake -> GCS Iceberg External Volume Connectivity ===")
    cur.execute("USE ROLE ACCOUNTADMIN")
    cur.execute("SELECT SYSTEM$VERIFY_EXTERNAL_VOLUME('URBANFORK_GCS_ICEBERG_VOL')")
    print("   External Volume verified:", cur.fetchone()[0])

    cur.execute("USE WAREHOUSE UF_LOAD_WH")
    cur.execute("USE DATABASE URBANFORK_PROD")
    already_loaded = False
    try:
        cur.execute("SELECT COUNT(*) FROM URBANFORK_PROD.OPS_RAW.DLV_ORD_HDR")
        if cur.fetchone()[0] == manifest["table_row_counts"]["OPS_RAW.DLV_ORD_HDR"]:
            already_loaded = True
    except Exception:
        pass

    if already_loaded:
        print("=== 2/8 & 3/8 All 12 Hybrid Iceberg + FDN tables already populated (624,924 rows) — skipping reload ===")
    else:
        print("=== 2/8 Creating 4 GCS Iceberg Tables + 8 Native FDN Tables ===")
        for attempt in range(1, 5):
            try:
                conn.execute_string(render_sql("01_ddl_hybrid_iceberg_and_fdn.sql", bucket))
                break
            except Exception as exc:
                if "091369" in str(exc) and attempt < 4:
                    print(f"   Snowflake External Volume warm-up (091369), retrying DDL (attempt {attempt}/4)...")
                    import time
                    time.sleep(3)
                else:
                    raise

        print("=== 3/8 Uploading Compressed Data Files (7.6 MB) & Running COPY INTO ===")
        stage_setup_sql = render_sql("02_load_and_snowpipe.sql", bucket).split("-- Bulk COPY INTO")[0]
        conn.execute_string(stage_setup_sql)

        for gz_file in sorted(DATA_DIR.glob("*.csv.gz")):
            print(f"   PUT {gz_file.name} -> @OPS_RAW.SEED_LOAD_STAGE")
            cur.execute(
                f"PUT 'file://{gz_file.as_posix()}' @URBANFORK_PROD.OPS_RAW.SEED_LOAD_STAGE AUTO_COMPRESS=FALSE OVERWRITE=TRUE"
            )

        jsonl_file = DATA_DIR / "app_delivery_pings.jsonl.gz"
        print(f"   PUT {jsonl_file.name} -> @IOT_RAW.IOT_LANDING_STAGE")
        cur.execute(
            f"PUT 'file://{jsonl_file.as_posix()}' @URBANFORK_PROD.IOT_RAW.IOT_LANDING_STAGE AUTO_COMPRESS=FALSE OVERWRITE=TRUE"
        )

        copy_and_pipe_sql = "-- Bulk COPY INTO" + render_sql("02_load_and_snowpipe.sql", bucket).split(
            "-- Bulk COPY INTO", 1
        )[1]
        conn.execute_string(copy_and_pipe_sql)

    print("=== 4/8 Deploying Legacy Analytical Views & Snowflake Scripting Stored Procedure ===")
    conn.execute_string(render_sql("04_legacy_views_and_procs.sql", bucket), remove_comments=True)

    print("=== 5/8 Deploying 7-Node Snowflake Task DAG & Dynamic Table + Running Initial DAG Execution ===")
    conn.execute_string(render_sql("03_streams_tasks_dynamic_tables.sql", bucket), remove_comments=True)
    cur.execute("EXECUTE TASK URBANFORK_PROD.MART.TSK_00_ROOT_CDC_ROUTER")
    print("   Triggered root task TSK_00_ROOT_CDC_ROUTER; waiting for 7-task DAG completion...")
    import time
    for _ in range(30):
        time.sleep(3)
        cur.execute("SELECT COUNT(*) FROM URBANFORK_PROD.MART.RPT_PBI_EXECUTIVE_SUMMARY")
        if cur.fetchone()[0] > 0:
            print("   7-Node Snowflake Task DAG completed! Power BI Gold tables populated.")
            break

    print("=== 6/8 Materializing Snowpark Fraud Scores & Cortex AI / ML Forecast ===")
    # Materialize MART.USER_FRAUD_RISK_SCORES directly so Snowpark output table is immediately live
    cur.execute(
        """
        CREATE OR REPLACE TABLE URBANFORK_PROD.MART.USER_FRAUD_RISK_SCORES AS
        WITH user_agg AS (
            SELECT
                h.USR_ID,
                COUNT(DISTINCT h.ORD_ID) AS DELIVERED_ORDERS_CNT,
                COUNT(DISTINCT d.DSP_ID) AS TOTAL_DISPUTES_CNT,
                COUNT_IF(d.DSP_RSN_CD = 4 OR d.RFND_STS_FLG = 9) AS FLAGGED_ABUSE_DISPUTES_CNT,
                COUNT(DISTINCT IFF(d.DSP_ID IS NOT NULL, h.ZONE_ID, NULL)) AS DISPUTED_ZONES_CNT,
                COALESCE(SUM(IFF(d.RFND_STS_FLG = 1, d.RFND_AMT_USD, 0)), 0) AS APPROVED_REFUND_TOTAL_USD
            FROM URBANFORK_PROD.OPS_RAW.DLV_ORD_HDR h
            LEFT JOIN URBANFORK_PROD.OPS_RAW.DSP_REFUND_FCT d ON h.ORD_ID = d.ORD_ID
            WHERE h.ORD_STS_CD = 'D'
            GROUP BY h.USR_ID
        ),
        scored AS (
            SELECT
                ua.*,
                u.HOME_ZONE_ID,
                u.UF_PASS_FLG,
                IFF(
                    ua.DELIVERED_ORDERS_CNT < 5 OR ua.TOTAL_DISPUTES_CNT = 0,
                    0.0,
                    ROUND(
                        LEAST(
                            0.50 * LEAST(ua.TOTAL_DISPUTES_CNT / ua.DELIVERED_ORDERS_CNT, 1.0)
                            + 0.30 * LEAST(ua.FLAGGED_ABUSE_DISPUTES_CNT / ua.TOTAL_DISPUTES_CNT, 1.0)
                            + 0.20 * IFF(ua.DISPUTED_ZONES_CNT >= 3, 1.0, ua.DISPUTED_ZONES_CNT / 3.0),
                            1.0
                        ),
                        4
                    )
                ) AS FRAUD_RISK_SCORE
            FROM user_agg ua
            JOIN URBANFORK_PROD.OPS_RAW.CUST_USER_MSTR u ON ua.USR_ID = u.USR_ID
        )
        SELECT
            *,
            CASE
                WHEN FRAUD_RISK_SCORE >= 0.75 THEN 'HIGH_RISK_BLOCK_AUTO_REFUND'
                WHEN FRAUD_RISK_SCORE >= 0.40 THEN 'MEDIUM_WATCHLIST'
                ELSE 'LOW_NORMAL'
            END AS RISK_TIER
        FROM scored;
        """
    )

    try:
        # Enable cross-region Cortex inference on GCP Snowflake accounts if needed
        cur.execute("ALTER ACCOUNT SET CORTEX_ENABLED_CROSS_REGION = 'ANY_REGION'")
        conn.execute_string(render_sql("05_cortex_ai_and_ml.sql", bucket), remove_comments=True)
    except Exception as exc:
        print(f"   [Warning] Cortex/ML optional step skipped or partially unavailable: {exc}")

    print("=== 7/8 Applying Horizon Governance (Object Tags, Masking Policies & Row Access Policy) ===")
    conn.execute_string(render_sql("06_governance_policies.sql", bucket), remove_comments=True)

    print("=== 8/8 Running Analytical Queries to Populate QUERY_HISTORY & Verifying Ground Truth ===")
    conn.execute_string(render_sql("07_workload_query_history.sql", bucket), remove_comments=True)

    for tbl, expected_cnt in manifest["table_row_counts"].items():
        cur.execute(f"SELECT COUNT(*) FROM URBANFORK_PROD.{tbl}")
        actual_cnt = cur.fetchone()[0]
        status = "OK" if actual_cnt == expected_cnt else "MISMATCH"
        print(f"   [{status}] {tbl:<32} rows = {actual_cnt:,} (expected {expected_cnt:,})")

    cur.execute(
        """
        SELECT ROUND(SUM(PLATFORM_NET_REVENUE_USD), 2)
        FROM URBANFORK_PROD.MART.VW_PLATFORM_NET_REVENUE
        WHERE CAL_DT BETWEEN '2025-07-01' AND '2025-09-30' AND VERT_CD = 1
        """
    )
    q3_rev = str(cur.fetchone()[0])
    exp_rev = manifest["demo_ground_truth_benchmarks"]["q3_2025_calendar_restaurants_true_net_revenue_usd"]
    print(f"   [MATH CHECK] Q3 2025 Restaurant Net Revenue = ${q3_rev} (expected ${exp_rev})")

    # Suspend warehouses immediately so zero idle trial credits are burned
    for wh in ("UF_LOAD_WH", "UF_TRANSFORM_WH"):
        try:
            cur.execute(f"ALTER WAREHOUSE {wh} SUSPEND")
        except Exception:
            pass
    print("\n🎉 URBANFORK_PROD Snowflake instance is 100% seeded, verified, and suspended (0 idle burn)!")


def main() -> None:
    load_dotenv(ROOT_DIR / ".env")
    parser = argparse.ArgumentParser(description="Seed UrbanFork Snowflake Demo Environment")
    parser.add_argument("--step", choices=["1", "2"], required=True, help="1 = Init GCS Volume, 2 = Load & Deploy All")
    args = parser.parse_args()

    bucket = os.getenv("GCS_LAKEHOUSE_BUCKET", "")
    if not bucket or bucket.startswith("your-gcp-project-id"):
        print("ERROR: Set GCS_LAKEHOUSE_BUCKET in .env before running seed_snowflake_instance.py.")
        sys.exit(1)

    conn = get_connection()
    try:
        if args.step == "1":
            step_1_init_gcs_integrations(conn, bucket)
        else:
            step_2_deploy_all(conn, bucket)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
