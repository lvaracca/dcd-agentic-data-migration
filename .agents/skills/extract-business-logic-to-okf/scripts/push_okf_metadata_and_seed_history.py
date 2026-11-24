#!/usr/bin/env python3
"""
Pushes extracted OKF table/column business descriptions into BigQuery metadata
AND replays translated Snowflake QUERY_HISTORY analytical queries on BigQuery
to seed deterministic Usage-Based Joins for Knowledge Catalog Data Insights!
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[4]
MANIFEST_PATH = ROOT_DIR / "okf" / "bigquery_metadata_manifest.json"


def run_bq_sql(project_id: str, region: str, sql: str) -> None:
    cmd = [
        "bq", "query",
        f"--project_id={project_id}",
        f"--location={region}",
        "--use_legacy_sql=false",
        "--label=datacloud:antigravity",
        sql,
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Warning on BQ SQL:\n{res.stderr}", file=sys.stderr)


def main() -> None:
    load_dotenv(ROOT_DIR / ".env")
    project_id = os.environ["GCP_PROJECT_ID"]
    region = os.environ.get("GCP_REGION", "us-central1")
    raw_ds = os.environ.get("BQ_RAW_DATASET", "quickbite_raw_ops")
    iot_ds = os.environ.get("BQ_IOT_DATASET", "quickbite_raw_iot")

    if MANIFEST_PATH.exists():
        print(f"=== 1/2 Pushing OKF Table & Column Descriptions from {MANIFEST_PATH.name} to BigQuery ===")
        meta = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        # Expected schema: {"tables": [{"dataset": "...", "table": "...", "description": "...", "columns": {"COL": "desc"}}]}
        for t in meta.get("tables", []):
            ds = t["dataset"]
            tbl = t["table"]
            t_desc = t.get("description", "").replace('"', '\\"').replace("'", "\\'")
            col_alters = []
            for col_nm, col_desc in t.get("columns", {}).items():
                esc = col_desc.replace('"', '\\"').replace("'", "\\'")
                col_alters.append(f"ALTER COLUMN `{col_nm}` SET OPTIONS (description = '{esc}')")

            ddl_parts = [f"ALTER TABLE `{project_id}.{ds}.{tbl}` SET OPTIONS (description = '{t_desc}');"]
            if col_alters:
                ddl_parts.append(f"ALTER TABLE `{project_id}.{ds}.{tbl}` " + ", ".join(col_alters) + ";")
            run_bq_sql(project_id, region, "\n".join(ddl_parts))
            print(f"   [Enriched] {ds}.{tbl} ({len(col_alters)} columns documented)")
    else:
        print(f"Note: {MANIFEST_PATH} not found yet; skipping description push.")

    print("=== 2/2 Replaying Translated Snowflake QUERY_HISTORY Joins to Seed Data Insights ===")
    seed_queries = f"""
    -- Seed 1: Multi-table SCD2 Commission + Order Basket + Calendar + Zone Join
    SELECT
      z.REG_CD,
      cal.FISC_YR_N,
      cal.FISC_QTR_N,
      ROUND(SUM(ln.QTY_N * ln.UNIT_PRC_USD * scd.COMM_RATE_PCT), 2) AS TRUE_COMM_USD
    FROM `{project_id}.{raw_ds}.DLV_ORD_HDR` h
    JOIN `{project_id}.{raw_ds}.DLV_ORD_ITEM_LN` ln ON h.ORD_ID = ln.ORD_ID
    JOIN `{project_id}.{raw_ds}.SYS_CAL_DIM` cal ON h.ORD_DT_SK = cal.DT_SK
    JOIN `{project_id}.{raw_ds}.GEO_ZONE_LKP` z ON h.ZONE_ID = z.ZONE_ID
    JOIN `{project_id}.{raw_ds}.MRC_COMM_SCD2` scd
      ON h.MRC_ID = scd.MRC_ID
     AND cal.CAL_DT BETWEEN scd.EFF_FROM_DT AND scd.EFF_TO_DT
    WHERE h.ORD_STS_CD = 'D'
    GROUP BY 1, 2, 3;

    -- Seed 2: Implicit Chargeback String-Concatenation Join ('CBK-' || ORD_ID)
    SELECT
      m.MRC_NM,
      z.CITY_NM,
      COUNT(DISTINCT d.DSP_ID) AS QUALITY_DISPUTES,
      SUM(ABS(led.LEDGER_AMT_USD)) AS RECOVERED_CBK_USD
    FROM `{project_id}.{raw_ds}.DSP_REFUND_FCT` d
    JOIN `{project_id}.{raw_ds}.DLV_ORD_HDR` h ON d.ORD_ID = h.ORD_ID
    JOIN `{project_id}.{raw_ds}.MRC_PARTNER_MSTR` m ON h.MRC_ID = m.MRC_ID
    JOIN `{project_id}.{raw_ds}.GEO_ZONE_LKP` z ON m.ZONE_ID = z.ZONE_ID
    JOIN `{project_id}.{raw_ds}.MRC_PAYOUT_LEDGER` led
      ON CONCAT('CBK-', h.ORD_ID) = led.REF_DOC_TXT
    WHERE d.RFND_STS_FLG = 1 AND d.DSP_RSN_CD IN (1, 2)
    GROUP BY 1, 2;

    -- Seed 3: Latest Snapshot Fleet Supply + User + Courier + Native JSON Telemetry Join
    SELECT
      u.QB_PASS_FLG,
      c.VEH_TP_CD,
      COUNT(DISTINCT h.ORD_ID) AS ORDERS_CNT,
      ROUND(AVG(LAX_INT64(p.PAYLOAD.metrics.travel_sec) / 60.0), 2) AS AVG_TRAVEL_MIN
    FROM `{project_id}.{raw_ds}.DLV_ORD_HDR` h
    JOIN `{project_id}.{raw_ds}.CUST_USER_MSTR` u ON h.USR_ID = u.USR_ID
    JOIN `{project_id}.{raw_ds}.CRR_COURIER_MSTR` c ON h.CRR_ID = c.CRR_ID
    JOIN `{project_id}.{iot_ds}.APP_DELIVERY_PINGS` p ON h.ORD_ID = p.ORD_ID
    WHERE h.ORD_STS_CD = 'D'
      AND LAX_STRING(p.PAYLOAD.stage) = 'DELIVERED'
      AND LAX_STRING(p.PAYLOAD.app_ver) != '3.8.0-beta'
    GROUP BY 1, 2;
    """
    run_bq_sql(project_id, region, seed_queries)
    print("✅ BigQuery query history seeded with deterministic multi-table join patterns!")


if __name__ == "__main__":
    main()
