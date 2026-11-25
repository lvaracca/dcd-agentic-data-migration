#!/usr/bin/env python3
"""
Programmatic Airbyte OSS Controller (Runs over IAP SSH against quickbite-airbyte-vm).
Automates:
  1. `setup-legacy-snowflake`: Configures Source (PostgreSQL OLTP) -> Destination
     (Snowflake URBANFORK_PROD) + Incremental Connection, and runs initial sync!
  2. `cutover-to-bigquery`: Seamlessly creates the Google BigQuery destination
     (using GCE Service Account ADC — zero JSON keys!) and switches the active
     incremental pipeline from Snowflake to BigQuery!
  3. `trigger-sync`: Triggers an immediate sync on the active connection and
     waits for job completion.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import subprocess
import sys
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent

REMOTE_WORKER_SCRIPT = r'''
import json, os, re, subprocess, sys, time, urllib.request, urllib.error

cfg = json.loads(sys.stdin.read())
action = cfg["action"]

# Extract client_id and client_secret from `abctl local credentials`
cred_out = subprocess.check_output(["sg", "docker", "-c", "abctl local credentials"], text=True)
ansi_clean = re.sub(r"\x1b\[[0-9;]*m", "", cred_out)
cid_m = re.search(r"Client-Id:\s*(\S+)", ansi_clean, re.I)
sec_m = re.search(r"Client-Secret:\s*(\S+)", ansi_clean, re.I)
if not cid_m or not sec_m:
    raise RuntimeError(f"Could not parse Client-Id/Client-Secret from abctl output:\n{ansi_clean}")
client_id, client_secret = cid_m.group(1), sec_m.group(1)

BASE = "http://localhost:8000/api/public/v1"

def api(method: str, path: str, body: dict | None = None, token: str | None = None) -> dict:
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(f"{BASE}{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        err_body = e.read().decode()
        raise RuntimeError(f"HTTP {e.code} on {method} {path}: {err_body}")

tok = api("POST", "/applications/token", {"client_id": client_id, "client_secret": client_secret})["access_token"]
ws_id = api("GET", "/workspaces", token=tok)["data"][0]["workspaceId"]

# Get VM internal IP so Airbyte kind pods reach urbanfork-oltp-postgres on 5439
vm_ip = subprocess.check_output(["hostname", "-I"], text=True).split()[0]

def get_or_create_pg_source() -> str:
    existing = api("GET", f"/sources?workspaceIds={ws_id}", token=tok).get("data", [])
    for s in existing:
        if s.get("name") == "UrbanFork OLTP Production (PostgreSQL)":
            return s["sourceId"]
    created = api("POST", "/sources", {
        "name": "UrbanFork OLTP Production (PostgreSQL)",
        "workspaceId": ws_id,
        "configuration": {
            "sourceType": "postgres",
            "host": vm_ip,
            "port": 5439,
            "database": "urbanfork_oltp",
            "schemas": ["oltp"],
            "username": "uf_airbyte_user",
            "password": "uf_demo_password",
            "ssl_mode": {"mode": "disable"},
            "tunnel_method": {"tunnel_method": "NO_TUNNEL"},
            "replication_method": {"method": "Standard"}
        }
    }, token=tok)
    return created["sourceId"]

def get_or_create_sf_dest() -> str:
    existing = api("GET", f"/destinations?workspaceIds={ws_id}", token=tok).get("data", [])
    for d in existing:
        if d.get("name") == "Snowflake - URBANFORK_PROD (Legacy)":
            return d["destinationId"]
    created = api("POST", "/destinations", {
        "name": "Snowflake - URBANFORK_PROD (Legacy)",
        "workspaceId": ws_id,
        "configuration": {
            "destinationType": "snowflake",
            "host": f"{cfg['sf_account']}.snowflakecomputing.com",
            "role": "ACCOUNTADMIN",
            "warehouse": "UF_LOAD_WH",
            "database": "URBANFORK_PROD",
            "schema": "OPS_RAW",
            "username": cfg["sf_user"],
            "credentials": {
                "auth_type": "Programmatic Access Token",
                "programmatic_access_token": cfg["sf_password"]
            }
        }
    }, token=tok)
    return created["destinationId"]

def get_or_create_bq_dest() -> str:
    existing = api("GET", f"/destinations?workspaceIds={ws_id}", token=tok).get("data", [])
    for d in existing:
        if d.get("name") == "Google BigQuery - UrbanFork Lakehouse":
            return d["destinationId"]
    created = api("POST", "/destinations", {
        "name": "Google BigQuery - UrbanFork Lakehouse",
        "workspaceId": ws_id,
        "configuration": {
            "destinationType": "bigquery",
            "project_id": cfg["gcp_project_id"],
            "dataset_id": cfg["bq_raw_dataset"],
            "dataset_location": cfg["gcp_region"],
            "loading_method": {"method": "Standard"}
        }
    }, token=tok)
    return created["destinationId"]

STREAM_CONFS = [
    {"name": "dlv_ord_hdr", "syncMode": "incremental_deduped_history", "cursorField": ["updated_at"], "primaryKey": [["ord_id"]]},
    {"name": "dlv_ord_item_ln", "syncMode": "incremental_deduped_history", "cursorField": ["updated_at"], "primaryKey": [["ord_ln_id"]]},
    {"name": "dsp_refund_fct", "syncMode": "incremental_deduped_history", "cursorField": ["updated_at"], "primaryKey": [["dsp_id"]]},
]

def run_and_wait_sync(conn_id: str) -> dict:
    job = api("POST", "/jobs", {"connectionId": conn_id, "jobType": "sync"}, token=tok)
    jid = job["jobId"]
    for _ in range(150):
        time.sleep(4)
        st = api("GET", f"/jobs/{jid}", token=tok)
        if st["status"] in ("succeeded", "failed", "cancelled"):
            return st
    return {"jobId": jid, "status": "running"}

if action == "setup-legacy-snowflake":
    src_id = get_or_create_pg_source()
    sf_dst_id = get_or_create_sf_dest()
    conns = api("GET", f"/connections?workspaceIds={ws_id}", token=tok).get("data", [])
    sf_conn_id = None
    for c in conns:
        if c.get("name") == "UrbanFork OLTP -> Snowflake (Legacy)":
            sf_conn_id = c["connectionId"]
            break
    if not sf_conn_id:
        c_res = api("POST", "/connections", {
            "name": "UrbanFork OLTP -> Snowflake (Legacy)",
            "sourceId": src_id,
            "destinationId": sf_dst_id,
            "namespaceDefinition": "destination",
            "prefix": "CDC_",
            "status": "active",
            "schedule": {"scheduleType": "manual"},
            "configurations": {"streams": STREAM_CONFS}
        }, token=tok)
        sf_conn_id = c_res["connectionId"]
    job_res = run_and_wait_sync(sf_conn_id)
    print(json.dumps({"status": "ok", "mode": "snowflake", "connectionId": sf_conn_id, "syncJob": job_res}, indent=2))

elif action == "cutover-to-bigquery":
    src_id = get_or_create_pg_source()
    bq_dst_id = get_or_create_bq_dest()
    conns = api("GET", f"/connections?workspaceIds={ws_id}", token=tok).get("data", [])
    bq_conn_id = None
    for c in conns:
        if c.get("name") == "UrbanFork OLTP -> Snowflake (Legacy)" and c.get("status") == "active":
            api("PATCH", f"/connections/{c['connectionId']}", {"status": "inactive"}, token=tok)
        if c.get("name") == "UrbanFork OLTP -> BigQuery (Live Cutover)":
            bq_conn_id = c["connectionId"]
            api("PATCH", f"/connections/{bq_conn_id}", {"status": "active"}, token=tok)
    if not bq_conn_id:
        c_res = api("POST", "/connections", {
            "name": "UrbanFork OLTP -> BigQuery (Live Cutover)",
            "sourceId": src_id,
            "destinationId": bq_dst_id,
            "namespaceDefinition": "destination",
            "prefix": "CDC_",
            "status": "active",
            "schedule": {"scheduleType": "manual"},
            "configurations": {"streams": STREAM_CONFS}
        }, token=tok)
        bq_conn_id = c_res["connectionId"]
    print(json.dumps({"status": "ok", "mode": "bigquery_cutover_complete", "bigqueryConnectionId": bq_conn_id}, indent=2))

elif action == "trigger-sync":
    conns = api("GET", f"/connections?workspaceIds={ws_id}", token=tok).get("data", [])
    active = [c for c in conns if c.get("status") == "active"]
    if not active:
        raise RuntimeError("No active Airbyte connection found!")
    job_res = run_and_wait_sync(active[0]["connectionId"])
    print(json.dumps({"status": "ok", "connection": active[0]["name"], "syncJob": job_res}, indent=2))
'''


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--action",
        choices=["setup-legacy-snowflake", "cutover-to-bigquery", "trigger-sync"],
        required=True,
    )
    args = parser.parse_args()

    load_dotenv(ROOT_DIR / ".env")
    project_id = os.environ["GCP_PROJECT_ID"]
    region = os.environ.get("GCP_REGION", "us-central1")
    zone = f"{region}-a"

    payload = {
        "action": args.action,
        "sf_account": os.environ["SNOWFLAKE_ACCOUNT"],
        "sf_user": os.environ["SNOWFLAKE_USER"],
        "sf_password": os.environ["SNOWFLAKE_PASSWORD"],
        "gcp_project_id": project_id,
        "gcp_region": region,
        "bq_raw_dataset": os.environ.get("BQ_RAW_DATASET", "urbanfork_raw_ops"),
    }

    b64_script = base64.b64encode(REMOTE_WORKER_SCRIPT.encode()).decode()
    env = os.environ.copy()
    env["CLOUDSDK_METRICS_ENVIRONMENT"] = (
        f"{env.get('CLOUDSDK_METRICS_ENVIRONMENT', '')} datacloud.antigravity".strip()
    )

    cmd = [
        "gcloud", "compute", "ssh", "quickbite-airbyte-vm",
        f"--zone={zone}",
        f"--project={project_id}",
        "--tunnel-through-iap",
        "--ssh-flag=-o ServerAliveInterval=15",
        f"--command=python3 -c \"import base64; exec(base64.b64decode('{b64_script}').decode())\"",
    ]
    res = subprocess.run(cmd, input=json.dumps(payload), text=True, capture_output=True, env=env)
    if res.returncode != 0:
        print("Airbyte Controller Error:\n", res.stderr, res.stdout, file=sys.stderr)
        sys.exit(1)
    print(res.stdout)


if __name__ == "__main__":
    main()
