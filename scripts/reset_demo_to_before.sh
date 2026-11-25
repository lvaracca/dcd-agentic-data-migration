#!/usr/bin/env bash
# ==============================================================================
# UrbanFork Demo — Reset Target GCP / Airbyte / Local Repo Back to "BEFORE" State
# Run ONLY when you want to wipe the dry-run artifacts and start a fresh recording
# from Act 1. (Never touches Snowflake URBANFORK_PROD!)
# ==============================================================================
set -euo pipefail

export CLOUDSDK_METRICS_ENVIRONMENT="${CLOUDSDK_METRICS_ENVIRONMENT:+$CLOUDSDK_METRICS_ENVIRONMENT }datacloud.antigravity"

if [[ -f .env ]]; then
  set -a
  source .env
  set +a
fi

PROJECT_ID="${GCP_PROJECT_ID:-dcd-migration-demo}"
REGION="${GCP_REGION:-us-central1}"
ZONE="${REGION}-a"

echo "⚠️  This will reset BigQuery target datasets, Airbyte active connection (back to Snowflake),"
echo "   PostgreSQL OLTP April 1st test orders, and local generated folders (gcp-target/, okf/, bundle/)."
echo "   Snowflake URBANFORK_PROD is NOT touched."
read -r -p "Continue? [y/N] " confirm
if [[ ! "${confirm}" =~ ^[Yy]$ ]]; then
  echo "Cancelled."
  exit 0
fi

echo "=== 1/4 Cleaning BigQuery target datasets in ${PROJECT_ID} (${REGION}) ==="
for ds in urbanfork_raw_ops urbanfork_raw_iot urbanfork_gold_mart urbanfork_gold_mart_assertions; do
  bq rm -r -f -d "${PROJECT_ID}:${ds}" >/dev/null 2>&1 || true
done
for ds in urbanfork_raw_ops urbanfork_raw_iot urbanfork_gold_mart; do
  bq mk --location="${REGION}" --label=datacloud:antigravity --dataset "${PROJECT_ID}:${ds}"
done

echo "=== 2/4 Resetting PostgreSQL OLTP (removing April 1st simulated orders) ==="
gcloud compute ssh quickbite-airbyte-vm \
  --zone="${ZONE}" \
  --project="${PROJECT_ID}" \
  --tunnel-through-iap \
  --command="sudo docker exec -i urbanfork-oltp-postgres psql -U uf_airbyte_user -d urbanfork_oltp -c \"DELETE FROM oltp.dlv_ord_item_ln WHERE ord_id > 'ORD-0090000'; DELETE FROM oltp.dlv_ord_hdr WHERE ord_id > 'ORD-0090000';\""

echo "=== 3/4 Restoring Airbyte Active Connection back to Snowflake (Legacy) ==="
.venv/bin/python - << 'PY'
import base64, json, os, subprocess
from dotenv import load_dotenv
load_dotenv('.env')
project_id = os.environ['GCP_PROJECT_ID']
zone = f"{os.environ.get('GCP_REGION', 'us-central1')}-a"
remote = r'''
import json, re, subprocess, urllib.request
cred_out = subprocess.check_output(["sg", "docker", "-c", "abctl local credentials"], text=True)
clean = re.sub(r"\x1b\[[0-9;]*m", "", cred_out)
cid = re.search(r"Client-Id:\s*(\S+)", clean, re.I).group(1)
sec = re.search(r"Client-Secret:\s*(\S+)", clean, re.I).group(1)
BASE = "http://localhost:8000/api/public/v1"
def api(method, path, body=None, tok=None):
    h = {"Accept": "application/json", "Content-Type": "application/json"}
    if tok: h["Authorization"] = f"Bearer {tok}"
    req = urllib.request.Request(f"{BASE}{path}", data=json.dumps(body).encode() if body else None, headers=h, method=method)
    with urllib.request.urlopen(req, timeout=60) as r:
        raw = r.read().decode()
        return json.loads(raw) if raw else {}
tok = api("POST", "/applications/token", {"client_id": cid, "client_secret": sec})["access_token"]
ws_id = api("GET", "/workspaces", tok=tok)["data"][0]["workspaceId"]
for c in api("GET", f"/connections?workspaceIds={ws_id}", tok=tok).get("data", []):
    if "BigQuery" in c.get("name", ""):
        api("DELETE", f"/connections/{c['connectionId']}", tok=tok)
    elif "Snowflake" in c.get("name", ""):
        api("PATCH", f"/connections/{c['connectionId']}", {"status": "active"}, tok=tok)
for d in api("GET", f"/destinations?workspaceIds={ws_id}", tok=tok).get("data", []):
    if "BigQuery" in d.get("name", ""):
        api("DELETE", f"/destinations/{d['destinationId']}", tok=tok)
print("Airbyte restored to Legacy Snowflake active state.")
'''
b64 = base64.b64encode(remote.encode()).decode()
env = os.environ.copy()
env["CLOUDSDK_METRICS_ENVIRONMENT"] = f"{env.get('CLOUDSDK_METRICS_ENVIRONMENT', '')} datacloud.antigravity".strip()
subprocess.run([
    "gcloud", "compute", "ssh", "quickbite-airbyte-vm",
    f"--zone={zone}", f"--project={project_id}", "--tunnel-through-iap",
    f"--command=python3 -c \"import base64; exec(base64.b64decode('{b64}').decode())\""
], check=True, env=env)
PY

echo "=== 4/4 Cleaning local generated target folders (keeping scripts & docs) ==="
rm -rf gcp-target/MIGRATION_AUDIT_REPORT.md okf bundle
echo "Note: To revert bi-powerbi/*.tmdl and ingestion-airbyte/airbyte_terraform/main.tf back to Snowflake, run:"
echo "  git checkout -- bi-powerbi/ ingestion-airbyte/airbyte_terraform/main.tf"
echo "✅ Environment reset to clean BEFORE-migration state!"
