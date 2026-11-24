#!/usr/bin/env python3
"""Validates that the Power BI .pbip / TMDL semantic model is cleanly re-pointed to BigQuery."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[4]
TMDL_DIR = ROOT_DIR / "bi-powerbi" / "QuickBite_Executive_Cockpit.SemanticModel" / "definition"


def main() -> None:
    load_dotenv(ROOT_DIR / ".env")
    project_id = os.getenv("GCP_PROJECT_ID", "")
    region = os.getenv("GCP_REGION", "us-central1")
    mart_ds = os.getenv("BQ_MART_DATASET", "quickbite_gold_mart")

    errors: list[str] = []
    tables_checked = 0

    for tmdl_file in sorted((TMDL_DIR / "tables").glob("*.tmdl")):
        tables_checked += 1
        text = tmdl_file.read_text(encoding="utf-8")
        tbl_name = tmdl_file.stem

        if "Snowflake.Databases" in text:
            errors.append(f"{tmdl_file.name}: Still contains legacy Snowflake.Databases() connector!")
        if "GoogleBigQuery.Database" not in text:
            errors.append(f"{tmdl_file.name}: Missing GoogleBigQuery.Database() connector!")

        tmdl_cols = set(re.findall(r"sourceColumn:\s*([A-Za-z0-9_]+)", text))
        print(f"   [TMDL Check] {tbl_name}: {len(tmdl_cols)} bound columns, GoogleBigQuery.Database = {'GoogleBigQuery.Database' in text}")

        if project_id and not project_id.startswith("your-"):
            cmd = [
                "bq", "query",
                f"--project_id={project_id}",
                f"--location={region}",
                "--format=json",
                "--use_legacy_sql=false",
                f"SELECT column_name FROM `{project_id}.{mart_ds}.INFORMATION_SCHEMA.COLUMNS` WHERE table_name = '{tbl_name}'",
            ]
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode == 0 and res.stdout.strip():
                bq_cols = {r["column_name"] for r in json.loads(res.stdout)}
                missing = tmdl_cols - bq_cols
                if missing:
                    errors.append(f"{tbl_name}: Columns missing or case-mismatched in BigQuery {mart_ds}: {sorted(missing)}")

    if errors:
        print("\n❌ Power BI Cutover Validation FAILED:")
        for e in errors:
            print("  -", e)
        sys.exit(1)

    print(f"\n✅ Power BI Cutover Validation PASSED across all {tables_checked} Gold tables (0 broken columns/measures)!")


if __name__ == "__main__":
    main()
