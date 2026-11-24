#!/usr/bin/env python3
"""
Live Order Traffic Simulator for Airbyte Cutover Demo (Act 2).
Injects N incremental orders (ORD-0090001+) into quickbite-oltp-postgres running
on the GCE VM `quickbite-airbyte-vm` via IAP SSH (no local Docker needed on Mac!).
"""

from __future__ import annotations

import argparse
import os
import random
import subprocess
import sys
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent


def inject_live_orders(count: int, start_seq: int) -> None:
    load_dotenv(ROOT_DIR / ".env")
    project_id = os.getenv("GCP_PROJECT_ID", "dcd-migration-demo")
    region = os.getenv("GCP_REGION", "us-central1")
    zone = f"{region}-a"

    rng = random.Random(100 + start_seq)
    zones = ["ZNE-LON-01", "ZNE-NYC-01", "ZNE-PAR-01", "ZNE-TYO-01"]
    sql_lines = ["BEGIN;"]

    ln_seq = 900000 + (start_seq * 2)
    for idx in range(count):
        seq = start_seq + idx
        oid = f"ORD-{seq:07d}"
        zid = zones[idx % len(zones)]
        mrc = f"MRC-{(idx % 40) + 1:04d}"
        usr = f"USR-{(idx % 500) + 100:06d}"
        crr = f"CRR-{(idx % 100) + 1:05d}"
        minute = idx % 60
        ts = f"2026-04-01 12:{minute:02d}:15"
        qty = rng.randint(1, 3)
        prc = 16.00
        srv = round(qty * prc * 0.08, 2)

        sql_lines.append(
            f"INSERT INTO oltp.dlv_ord_hdr VALUES ("
            f"'{oid}', 20260401, '{ts}', '{usr}', '{mrc}', '{crr}', '{zid}', "
            f"1, 'D', 3.99, {srv:.2f}, 3.00, 5.25, 0.00, '{ts}') ON CONFLICT DO NOTHING;"
        )
        ln_seq += 1
        sql_lines.append(
            f"INSERT INTO oltp.dlv_ord_item_ln VALUES ("
            f"'LN-{ln_seq:08d}', '{oid}', 'SKU-R03', 'Spicy Tuna Roll', {qty}, {prc:.2f}, '{ts}') "
            f"ON CONFLICT DO NOTHING;"
        )

    sql_lines.append("COMMIT;")
    sql_payload = "\n".join(sql_lines)

    env = os.environ.copy()
    env["CLOUDSDK_METRICS_ENVIRONMENT"] = (
        f"{env.get('CLOUDSDK_METRICS_ENVIRONMENT', '')} datacloud.antigravity".strip()
    )
    cmd = [
        "gcloud", "compute", "ssh", "quickbite-airbyte-vm",
        f"--zone={zone}",
        f"--project={project_id}",
        "--tunnel-through-iap",
        "--command=sudo docker exec -i quickbite-oltp-postgres psql -U qb_airbyte_user -d quickbite_oltp -v ON_ERROR_STOP=1",
    ]
    res = subprocess.run(cmd, input=sql_payload, text=True, capture_output=True, env=env)
    if res.returncode != 0:
        print("ERROR injecting live orders into quickbite-oltp-postgres on GCE VM:", res.stderr)
        sys.exit(1)

    print(f"✅ Injected {count} new live orders (ORD-{start_seq:07d} .. ORD-{start_seq + count - 1:07d}) @ 2026-04-01 into PostgreSQL OLTP!")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--count", type=int, default=50, help="Number of live orders to insert")
    p.add_argument("--start-seq", type=int, default=90001, help="Starting order sequence (> 90000)")
    args = p.parse_args()
    inject_live_orders(args.count, args.start_seq)
