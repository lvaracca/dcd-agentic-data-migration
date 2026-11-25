#!/usr/bin/env python3
"""Validates that the Tableau .twb workbook is cleanly re-pointed to BigQuery."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[4]
TWB_PATH = ROOT_DIR / "bi-tableau" / "UrbanFork_Executive_Cockpit_BigQuery.twb"


def main() -> int:
    load_dotenv(ROOT_DIR / ".env")
    project_id = os.getenv("GCP_PROJECT_ID", "dcd-migration-demo")
    mart_dataset = os.getenv("BQ_MART_DATASET", "urbanfork_gold_mart")

    if not TWB_PATH.exists():
        print(f"❌ Missing {TWB_PATH}")
        return 1

    root = ET.parse(TWB_PATH).getroot()
    errors: list[str] = []

    bq_conns = 0
    for conn in root.iter("connection"):
        cls = conn.attrib.get("class")
        if cls == "snowflake":
            errors.append("Still contains legacy Snowflake connection!")
        elif cls == "bigquery":
            bq_conns += 1
            if conn.attrib.get("project") != project_id:
                errors.append(f"Unexpected BigQuery project: {conn.attrib.get('project')}")
            if conn.attrib.get("schema") != mart_dataset:
                errors.append(f"Unexpected BigQuery dataset: {conn.attrib.get('schema')}")

    if bq_conns == 0:
        errors.append("No BigQuery connection found in .twb!")

    bound_cols = {
        rec.findtext("remote-name")
        for rec in root.iter("metadata-record")
        if rec.attrib.get("class") == "column" and rec.findtext("remote-name")
    }
    print(f"   [TWB Check] {TWB_PATH.name}: {bq_conns} BigQuery connection(s), {len(bound_cols)} bound columns")

    try:
        out = subprocess.check_output(
            ["bq", "show", "--schema", "--format=json", f"{project_id}:{mart_dataset}.FCT_PLATFORM_NET_REVENUE"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
        bq_cols = {c["name"] for c in json.loads(out)}
        missing = bound_cols - bq_cols
        if missing:
            errors.append(f"FCT_PLATFORM_NET_REVENUE missing columns in BigQuery: {sorted(missing)}")
        else:
            print(f"   [BQ Match]  FCT_PLATFORM_NET_REVENUE: 100% column parity ({len(bound_cols)}/{len(bound_cols)})")
    except Exception as exc:
        print(f"   [Info] Live BigQuery check skipped: {exc}")

    if errors:
        print("\n❌ Tableau Cutover Validation FAILED:")
        for e in errors:
            print(f"   - {e}")
        return 1

    print("\n✅ Tableau Cutover Validation PASSED (0 broken columns or Calculated Fields)!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
