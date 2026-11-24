#!/usr/bin/env python3
"""
Automated End-to-End Parity Verifier (Snowflake QUICKBITE_PROD vs. BigQuery).
Verifies:
  1. Row counts across all 12 Hybrid (Iceberg + FDN + JSON) tables
  2. Cent-accurate financial parity on Q3 2025 & FY 2025 Platform Net Revenue (SCD2)
  3. Anti-fanout Approved Refunds total ($248,632.85)
  4. Snapshot-safe Live Fleet Supply Deficit top 3 zones (5.50, 4.50, 3.25)
  5. Prime Partner count parity between Snowflake Task DAG & BigQuery Dataform DAG
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from decimal import Decimal
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
MANIFEST_PATH = ROOT_DIR / "data-generator" / "output" / "ground_truth_manifest.json"


def bq_scalar_or_rows(project_id: str, region: str, sql: str) -> list[dict]:
    cmd = [
        "bq", "query",
        f"--project_id={project_id}",
        f"--location={region}",
        "--format=json",
        "--use_legacy_sql=false",
        "--label=datacloud:antigravity",
        sql,
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"BigQuery query failed:\n{res.stderr}")
    return json.loads(res.stdout) if res.stdout.strip() else []


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--allow-airbyte-delta", action="store_true", help="Allow >= baseline rows for Airbyte live sync tables")
    parser.add_argument("--compare-live-snowflake", action="store_true", help="Also query live Snowflake MART for side-by-side diff")
    args = parser.parse_args()

    load_dotenv(ROOT_DIR / ".env")
    project_id = os.environ["GCP_PROJECT_ID"]
    region = os.environ.get("GCP_REGION", "us-central1")
    raw_ds = os.environ.get("BQ_RAW_DATASET", "quickbite_raw_ops")
    iot_ds = os.environ.get("BQ_IOT_DATASET", "quickbite_raw_iot")
    mart_ds = os.environ.get("BQ_MART_DATASET", "quickbite_gold_mart")

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    gt = manifest["demo_ground_truth_benchmarks"]
    failures = 0

    print("==========================================================================")
    print(" QUICKBITE MIGRATION PARITY & MATHEMATICAL VERIFICATION SUITE")
    print("==========================================================================\n")

    # 1. Row Count Parity across all 12 tables
    print("--- 1. Table Row Count Parity (12 Hybrid Iceberg + FDN + JSON Tables) ---")
    union_parts = []
    for full_tbl, exp_cnt in manifest["table_row_counts"].items():
        schema_nm, tbl_nm = full_tbl.split(".")
        ds = iot_ds if schema_nm == "IOT_RAW" else raw_ds
        union_parts.append(f"SELECT '{full_tbl}' AS tbl, COUNT(*) AS cnt FROM `{project_id}.{ds}.{tbl_nm}`")

    rows = bq_scalar_or_rows(project_id, region, " UNION ALL ".join(union_parts))
    actual_counts = {r["tbl"]: int(r["cnt"]) for r in rows}

    airbyte_tables = {"OPS_RAW.DLV_ORD_HDR", "OPS_RAW.DLV_ORD_ITEM_LN", "OPS_RAW.DSP_REFUND_FCT"}
    for full_tbl, exp_cnt in manifest["table_row_counts"].items():
        act_cnt = actual_counts.get(full_tbl, -1)
        if act_cnt == exp_cnt or (args.allow_airbyte_delta and full_tbl in airbyte_tables and act_cnt >= exp_cnt):
            extra = f" (+{act_cnt - exp_cnt} live Airbyte rows)" if act_cnt > exp_cnt else ""
            print(f"  [PASS] {full_tbl:<30} BQ={act_cnt:>9,}{extra}")
        else:
            print(f"  [FAIL] {full_tbl:<30} BQ={act_cnt:>9,} != Expected={exp_cnt:>9,}")
            failures += 1

    # 2. Financial & Analytical Trap Benchmarks on Dataform Gold Marts
    print("\n--- 2. Dataform Gold Marts vs. Ground-Truth Financial Benchmarks ---")
    fin_sql = f"""
    SELECT
      ROUND(SUM(IF(CAL_DT BETWEEN '2025-07-01' AND '2025-09-30' AND VERT_CD = 1, PLATFORM_NET_REVENUE_USD, 0)), 2) AS q3_rest_net_rev,
      ROUND(SUM(IF(FISC_YR_N = 2025 AND VERT_CD = 1, PLATFORM_NET_REVENUE_USD, 0)), 2) AS fy25_rest_net_rev,
      ROUND(SUM(IF(FISC_YR_N = 2025 AND VERT_CD = 2, PLATFORM_NET_REVENUE_USD, 0)), 2) AS fy25_groc_net_rev,
      ROUND(SUM(IF(CAL_DT <= '2026-03-31', APPROVED_REFUNDS_USD, 0)), 2) AS total_approved_refunds
    FROM `{project_id}.{mart_ds}.FCT_PLATFORM_NET_REVENUE`
    """
    fin = bq_scalar_or_rows(project_id, region, fin_sql)[0]

    checks = [
        ("Q3 2025 Restaurant Net Rev (SCD2 Check)", Decimal(str(fin["q3_rest_net_rev"])), Decimal(gt["q3_2025_calendar_restaurants_true_net_revenue_usd"])),
        ("FY 2025 Restaurant Net Rev (Fiscal Check)", Decimal(str(fin["fy25_rest_net_rev"])), Decimal(gt["fy2025_fiscal_net_revenue_restaurants_usd"])),
        ("FY 2025 Grocery Net Rev (Vertical Check)", Decimal(str(fin["fy25_groc_net_rev"])), Decimal(gt["fy2025_fiscal_net_revenue_grocery_usd"])),
        ("Approved Refunds Total (Anti-Fanout Check)", Decimal(str(fin["total_approved_refunds"])), Decimal(gt["all_time_true_approved_refunds_usd"])),
    ]
    for label, act_val, exp_val in checks:
        if act_val == exp_val:
            print(f"  [PASS] {label:<44} ${act_val:>12,.2f} == ${exp_val:>12,.2f}")
        else:
            print(f"  [FAIL] {label:<44} ${act_val:>12,.2f} != ${exp_val:>12,.2f}")
            failures += 1

    # 3. Fleet Supply Snapshot Trap Check
    snap_sql = f"""
    SELECT ZONE_ID, SUPPLY_DEFICIT_RATIO
    FROM `{project_id}.{mart_ds}.DT_LIVE_ZONE_SUPPLY_DEFICIT`
    ORDER BY SUPPLY_DEFICIT_RATIO DESC
    LIMIT 3
    """
    top3_bq = bq_scalar_or_rows(project_id, region, snap_sql)
    exp_top3 = [(z["zone_id"], float(z["supply_deficit_ratio"])) for z in gt["top_3_supply_deficit_zones_at_latest_snapshot"]]
    act_top3 = [(r["ZONE_ID"], float(r["SUPPLY_DEFICIT_RATIO"])) for r in top3_bq]
    if act_top3 == exp_top3:
        print(f"  [PASS] {'Top 3 Deficit Zones (Snapshot Trap Check)':<44} {act_top3}")
    else:
        print(f"  [FAIL] {'Top 3 Deficit Zones (Snapshot Trap Check)':<44} {act_top3} != {exp_top3}")
        failures += 1

    # 4. Optional Live Snowflake Side-by-Side Comparison
    if args.compare_live_snowflake:
        import snowflake.connector

        print("\n--- 3. Live Snowflake MART vs. BigQuery Dataform Gold Comparison ---")
        sf = snowflake.connector.connect(
            account=os.environ["SNOWFLAKE_ACCOUNT"],
            user=os.environ["SNOWFLAKE_USER"],
            password=os.environ["SNOWFLAKE_PASSWORD"],
            role=os.environ.get("SNOWFLAKE_ROLE", "ACCOUNTADMIN"),
            warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE", "QB_TRANSFORM_WH"),
            database="QUICKBITE_PROD",
        )
        try:
            cur = sf.cursor()
            cur.execute("SELECT COUNT_IF(IS_PRIME_PARTNER) FROM QUICKBITE_PROD.MART.DIM_PRIME_PARTNER_SCORECARD")
            sf_prime = int(cur.fetchone()[0])
            try:
                cur.execute("ALTER WAREHOUSE QB_TRANSFORM_WH SUSPEND")
            except Exception:
                pass
        finally:
            sf.close()

        bq_prime = int(
            bq_scalar_or_rows(
                project_id,
                region,
                f"SELECT COUNTIF(IS_PRIME_PARTNER) AS c FROM `{project_id}.{mart_ds}.DIM_PRIME_PARTNER_SCORECARD`",
            )[0]["c"]
        )
        if sf_prime == bq_prime:
            print(f"  [PASS] Active Prime Partners Count: Snowflake={sf_prime} == BigQuery={bq_prime}")
        else:
            print(f"  [FAIL] Active Prime Partners Count: Snowflake={sf_prime} != BigQuery={bq_prime}")
            failures += 1

    print("\n==========================================================================")
    if failures == 0:
        print(" ✅ 100.00% PARITY VERIFIED — READY FOR POWER BI & KNOWLEDGE CATALOG CUTOVER!")
    else:
        print(f" ❌ PARITY CHECK FAILED WITH {failures} DISCREPANCY(IES).")
        sys.exit(1)


if __name__ == "__main__":
    main()
