#!/usr/bin/env python3
"""
Automated Tableau Workbook (.twb XML) Cutover Helper:
Re-points Snowflake datasource connections inside a Tableau `.twb` workbook
to Google BigQuery (`dcd-migration-demo.urbanfork_gold_mart`) while keeping
100% of Tableau Calculated Fields, column bindings, and dashboard layouts intact.
"""

from __future__ import annotations

import argparse
import os
import xml.etree.ElementTree as ET
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent


def repoint_twb(input_path: Path, output_path: Path, project_id: str, dataset: str) -> None:
    tree = ET.parse(input_path)
    root = tree.getroot()
    updated = 0

    for conn in root.iter("connection"):
        if conn.attrib.get("class") == "snowflake":
            conn.attrib["class"] = "bigquery"
            conn.attrib["authentication"] = "oauth"
            conn.attrib["project"] = project_id
            conn.attrib["CATALOG"] = project_id
            conn.attrib["schema"] = dataset
            conn.attrib["connection-dialect"] = "google-sql"
            for sf_key in ("server", "warehouse", "role", "dbname", "username", "service"):
                conn.attrib.pop(sf_key, None)
            updated += 1

    for nc in root.iter("named-connection"):
        if "snowflake" in nc.attrib.get("caption", "").lower():
            nc.attrib["caption"] = project_id

    for ds in root.iter("datasource"):
        cap = ds.attrib.get("caption", "")
        if "Snowflake" in cap:
            ds.attrib["caption"] = cap.replace("Snowflake", "BigQuery")

    for rel in root.iter("relation"):
        tbl = rel.attrib.get("table", "")
        if "[MART]." in tbl:
            rel.attrib["table"] = tbl.replace("[MART].", f"[{dataset}].")

    tree.write(output_path, encoding="utf-8", xml_declaration=True)
    print(f"✅ Re-pointed {updated} Snowflake connection(s) to BigQuery ({project_id}.{dataset}) -> {output_path}")


def main() -> None:
    load_dotenv(ROOT_DIR / ".env")
    p = argparse.ArgumentParser(description="Re-point a Tableau .twb workbook from Snowflake to BigQuery")
    p.add_argument("--input", required=True, type=Path, help="Input Snowflake .twb file")
    p.add_argument("--output", type=Path, help="Output BigQuery .twb file (defaults to *_bigquery.twb)")
    args = p.parse_args()

    out = args.output or args.input.with_name(f"{args.input.stem}_bigquery.twb")
    repoint_twb(
        input_path=args.input,
        output_path=out,
        project_id=os.getenv("GCP_PROJECT_ID", "dcd-migration-demo"),
        dataset=os.getenv("BQ_MART_DATASET", "urbanfork_gold_mart"),
    )


if __name__ == "__main__":
    main()
