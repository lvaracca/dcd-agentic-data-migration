#!/usr/bin/env python3
"""Live Snowflake Estate Inspector for Act 1 Audit."""

from __future__ import annotations

import json
import os
from pathlib import Path
from dotenv import load_dotenv
import snowflake.connector

ROOT_DIR = Path(__file__).resolve().parents[4]


def main() -> None:
    load_dotenv(ROOT_DIR / ".env")
    conn = snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        password=os.environ["SNOWFLAKE_PASSWORD"],
        role=os.environ.get("SNOWFLAKE_ROLE", "ACCOUNTADMIN"),
        warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE", "QB_LOAD_WH"),
        database="QUICKBITE_PROD",
    )
    out: dict = {}
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT TABLE_SCHEMA, TABLE_NAME, TABLE_TYPE, IS_ICEBERG, ROW_COUNT, BYTES, CLUSTERING_KEY
            FROM QUICKBITE_PROD.INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA IN ('OPS_RAW', 'IOT_RAW', 'MART')
            ORDER BY TABLE_SCHEMA, TABLE_NAME
            """
        )
        cols = [c[0] for c in cur.description]
        out["tables_and_views"] = [dict(zip(cols, r)) for r in cur.fetchall()]

        cur.execute("SHOW TASKS IN SCHEMA QUICKBITE_PROD.MART")
        t_cols = [c[0] for c in cur.description]
        out["snowflake_task_dag"] = [
            {
                "name": dict(zip(t_cols, r)).get("name"),
                "state": dict(zip(t_cols, r)).get("state"),
                "schedule": dict(zip(t_cols, r)).get("schedule"),
                "predecessors": dict(zip(t_cols, r)).get("predecessors"),
                "warehouse": dict(zip(t_cols, r)).get("warehouse"),
            }
            for r in cur.fetchall()
        ]

        cur.execute("SHOW STREAMS IN SCHEMA QUICKBITE_PROD.OPS_RAW")
        s_cols = [c[0] for c in cur.description]
        out["streams"] = [dict(zip(s_cols, r)).get("name") for r in cur.fetchall()]

        cur.execute("SHOW MASKING POLICIES IN SCHEMA QUICKBITE_PROD.GOVERNANCE")
        m_cols = [c[0] for c in cur.description]
        out["masking_policies"] = [dict(zip(m_cols, r)).get("name") for r in cur.fetchall()]

        cur.execute("SHOW ROW ACCESS POLICIES IN SCHEMA QUICKBITE_PROD.GOVERNANCE")
        r_cols = [c[0] for c in cur.description]
        out["row_access_policies"] = [dict(zip(r_cols, r)).get("name") for r in cur.fetchall()]

        cur.execute("ALTER WAREHOUSE QB_LOAD_WH SUSPEND")
    except Exception as exc:
        out["warning"] = str(exc)
    finally:
        conn.close()

    report_json = ROOT_DIR / "gcp-target" / "snowflake_live_inventory.json"
    report_json.parent.mkdir(parents=True, exist_ok=True)
    report_json.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print(json.dumps(out, indent=2, default=str))


if __name__ == "__main__":
    main()
