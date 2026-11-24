#!/usr/bin/env bash
# ==============================================================================
# Opens an IAP TCP Tunnel on http://localhost:8000 to the Airbyte OSS Web UI
# running on quickbite-airbyte-vm (prints login email & password first!).
# ==============================================================================
set -euo pipefail

export CLOUDSDK_METRICS_ENVIRONMENT="${CLOUDSDK_METRICS_ENVIRONMENT:+$CLOUDSDK_METRICS_ENVIRONMENT }datacloud.antigravity"

if [[ -f .env ]]; then
  set -a
  source .env
  set +a
fi

PROJECT_ID="${GCP_PROJECT_ID:-dcd-migration-demo}"
ZONE="${GCP_REGION:-us-central1}-a"

echo "=== Fetching Airbyte OSS Login Credentials from quickbite-airbyte-vm ==="
gcloud compute ssh "quickbite-airbyte-vm" \
  --zone="${ZONE}" \
  --project="${PROJECT_ID}" \
  --tunnel-through-iap \
  --command="sg docker -c 'abctl local credentials'"

echo ""
echo "🌐 Opening IAP Tunnel -> Open http://localhost:8000 in Chrome! (Press Ctrl+C to close)"
gcloud compute start-iap-tunnel "quickbite-airbyte-vm" 8000 \
  --local-host-port=localhost:8000 \
  --zone="${ZONE}" \
  --project="${PROJECT_ID}"
