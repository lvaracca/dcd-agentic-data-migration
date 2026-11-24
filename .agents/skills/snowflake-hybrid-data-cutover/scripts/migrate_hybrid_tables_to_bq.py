#!/usr/bin/env python3
"""
Hybrid Snowflake -> BigQuery Data Migrator (Act 2):
  1. Mounts 4 GCS Apache Iceberg tables Zero-Copy via BigLake (`*_iceberg_ext`)
     and creates writable partitioned/clustered tables for live Airbyte sync.
  2. Unloads 8 Native Snowflake FDN tables (including VARIANT JSON) to GCS and
     loads them into BigQuery with native JSON, Partitioning, and Clustering.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from dotenv import load_dotenv
import snowflake.connector

ROOT_DIR = Path(__file__).resolve().parents[4]

ICEBERG_TABLES = [
    ("DLV_ORD_HDR", "PARTITION BY DATE(ORD_TS) CLUSTER BY VERT_CD, ORD_STS_CD"),
    ("DLV_ORD_ITEM_LN", "CLUSTER BY ORD_ID"),
    ("ZNE_FLEET_SNAP", "PARTITION BY DATE(SNAP_TS) CLUSTER BY ZONE_ID"),
    ("MRC_PAYOUT_LEDGER", "PARTITION BY ISSUE_DT CLUSTER BY PYT_STS_FLG, MRC_ID"),
]

FDN_RELATIONAL_TABLES = [
    ("SYS_CAL_DIM", ""),
    ("GEO_ZONE_LKP", ""),
    ("MRC_PARTNER_MSTR", "CLUSTER BY ZONE_ID, VERT_CD"),
    ("MRC_COMM_SCD2", "PARTITION BY EFF_FROM_DT CLUSTER BY MRC_ID"),
    ("CUST_USER_MSTR", "CLUSTER BY HOME_ZONE_ID, QB_PASS_FLG"),
    ("CRR_COURIER_MSTR", "CLUSTER BY HOME_ZONE_ID, VEH_TP_CD"),
    ("DSP_REFUND_FCT", "PARTITION BY DATE(DSP_TS) CLUSTER BY DSP_RSN_CD, RFND_STS_FLG"),
]


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
        print(f"BQ SQL Error:\n{sql}\n{res.stderr}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    load_dotenv(ROOT_DIR / ".env")
    project_id = os.environ["GCP_PROJECT_ID"]
    region = os.environ.get("GCP_REGION", "us-central1")
    bucket = os.environ["GCS_LAKEHOUSE_BUCKET"]
    conn_id = os.environ.get("BQ_BIGLAKE_CONNECTION", "biglake-iceberg-conn")
    raw_ds = os.environ.get("BQ_RAW_DATASET", "quickbite_raw_ops")
    iot_ds = os.environ.get("BQ_IOT_DATASET", "quickbite_raw_iot")

    sf = snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        password=os.environ["SNOWFLAKE_PASSWORD"],
        role=os.environ.get("SNOWFLAKE_ROLE", "ACCOUNTADMIN"),
        warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE", "QB_LOAD_WH"),
        database="QUICKBITE_PROD",
    )

    try:
        cur = sf.cursor()
        print("=== Part A: Zero-Copy BigLake Iceberg Mount for 4 High-Volume Tables ===")
        for tbl, part_spec in ICEBERG_TABLES:
            cur.execute(f"SELECT SYSTEM$GET_ICEBERG_TABLE_INFORMATION('QUICKBITE_PROD.OPS_RAW.{tbl}')")
            info = json.loads(cur.fetchone()[0])
            meta_uri = info["metadataLocation"].replace("gcs://", "gs://")
            print(f"   [Zero-Copy Iceberg] {tbl} -> {meta_uri}")

            ext_sql = f"""
            CREATE OR REPLACE EXTERNAL TABLE `{project_id}.{raw_ds}.{tbl}_ICEBERG_EXT`
            WITH CONNECTION `{project_id}.{region}.{conn_id}`
            OPTIONS (
              format = 'ICEBERG',
              uris = ['{meta_uri}']
            );
            CREATE OR REPLACE TABLE `{project_id}.{raw_ds}.{tbl}`
            {part_spec}
            AS SELECT * FROM `{project_id}.{raw_ds}.{tbl}_ICEBERG_EXT`;
            """
            run_bq_sql(project_id, region, ext_sql)

        print("=== Part B: Unloading 7 Native Relational FDN Tables to Parquet & Loading BQ ===")
        for tbl, part_spec in FDN_RELATIONAL_TABLES:
            gcs_prefix = f"fdn-export/{tbl.lower()}/"
            cur.execute(
                f"""
                COPY INTO @QUICKBITE_PROD.OPS_RAW.GCS_EXPORT_STAGE/{tbl.lower()}/
                FROM QUICKBITE_PROD.OPS_RAW.{tbl}
                FILE_FORMAT = (TYPE = PARQUET)
                HEADER = TRUE
                OVERWRITE = TRUE;
                """
            )
            load_sql = f"""
            LOAD DATA OVERWRITE `{project_id}.{raw_ds}.{tbl}`
            {part_spec}
            FROM FILES (
              format = 'PARQUET',
              uris = ['gs://{bucket}/{gcs_prefix}*.parquet']
            );
            """
            run_bq_sql(project_id, region, load_sql)
            print(f"   [FDN Parquet -> BQ] {tbl} migrated.")

        print("=== Part C: Migrating Semi-Structured VARIANT Table -> BigQuery Native JSON ===")
        cur.execute(
            """
            COPY INTO @QUICKBITE_PROD.OPS_RAW.GCS_EXPORT_STAGE/app_delivery_pings_json/data
            FROM (
                SELECT OBJECT_CONSTRUCT(
                    'PING_ID', PING_ID,
                    'INGEST_TS', TO_VARCHAR(INGEST_TS, 'YYYY-MM-DD HH24:MI:SS'),
                    'ORD_ID', ORD_ID,
                    'PAYLOAD', PAYLOAD
                )
                FROM QUICKBITE_PROD.IOT_RAW.APP_DELIVERY_PINGS
            )
            FILE_FORMAT = (TYPE = JSON COMPRESSION = GZIP)
            OVERWRITE = TRUE;
            """
        )
        json_sql = f"""
        LOAD DATA OVERWRITE `{project_id}.{iot_ds}.APP_DELIVERY_PINGS` (
          PING_ID STRING,
          INGEST_TS TIMESTAMP,
          ORD_ID STRING,
          PAYLOAD JSON
        )
        PARTITION BY DATE(INGEST_TS)
        CLUSTER BY ORD_ID
        FROM FILES (
          format = 'JSON',
          uris = ['gs://{bucket}/fdn-export/app_delivery_pings_json/*.json.gz']
        );
        """
        run_bq_sql(project_id, region, json_sql)
        print("   [VARIANT -> Native BQ JSON] APP_DELIVERY_PINGS migrated.")

        try:
            cur.execute("ALTER WAREHOUSE QB_LOAD_WH SUSPEND")
        except Exception:
            pass
    finally:
        sf.close()

    print("\n✅ All 12 Hybrid Snowflake tables (Iceberg + FDN + VARIANT) are live in BigQuery!")


if __name__ == "__main__":
    main()
