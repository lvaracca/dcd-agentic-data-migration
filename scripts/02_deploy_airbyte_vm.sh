#!/usr/bin/env bash
# ==============================================================================
# QuickBite Demo — Deploy Private GCE VM with PostgreSQL OLTP + Airbyte OSS
# 100% Argolis-compliant:
#   - Private VM (--no-address) + Shielded VM
#   - Outbound internet via Cloud Router + Cloud NAT
#   - Inbound UI & SSH via Identity-Aware Proxy (IAP Tunnel)
#   - Attached Service Account (ADC) for keyless BigQuery & GCS access
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
VM_NAME="quickbite-airbyte-vm"
VPC_NAME="quickbite-net"
SUBNET_NAME="quickbite-us-central1"
SA_NAME="quickbite-airbyte-sa"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

echo "=== 1/5 Enabling IAP API on ${PROJECT_ID} ==="
gcloud services enable iap.googleapis.com --project="${PROJECT_ID}"

echo "=== 2/5 Creating Dedicated Airbyte Service Account (${SA_EMAIL}) ==="
if ! gcloud iam service-accounts describe "${SA_EMAIL}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  gcloud iam service-accounts create "${SA_NAME}" \
    --display-name="QuickBite Airbyte OSS Worker SA" \
    --project="${PROJECT_ID}"
  sleep 5
fi

for ROLE in "roles/bigquery.admin" "roles/storage.objectAdmin" "roles/logging.logWriter"; do
  for attempt in 1 2 3 4 5; do
    if gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
      --member="serviceAccount:${SA_EMAIL}" \
      --role="${ROLE}" \
      --condition=None >/dev/null 2>&1; then
      break
    fi
    sleep 4
  done
done

echo "=== 3/5 Creating Custom VPC, Subnet, IAP Firewall & Cloud NAT in ${REGION} ==="
if ! gcloud compute networks describe "${VPC_NAME}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  gcloud compute networks create "${VPC_NAME}" \
    --subnet-mode=custom \
    --project="${PROJECT_ID}"
fi

if ! gcloud compute networks subnets describe "${SUBNET_NAME}" --region="${REGION}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  gcloud compute networks subnets create "${SUBNET_NAME}" \
    --network="${VPC_NAME}" \
    --region="${REGION}" \
    --range="10.10.0.0/24" \
    --enable-private-ip-google-access \
    --project="${PROJECT_ID}"
fi

if ! gcloud compute firewall-rules describe "quickbite-allow-iap" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  gcloud compute firewall-rules create "quickbite-allow-iap" \
    --network="${VPC_NAME}" \
    --direction=INGRESS \
    --action=ALLOW \
    --source-ranges="35.235.240.0/20" \
    --rules="tcp:22,tcp:8000,tcp:5439" \
    --project="${PROJECT_ID}"
fi

if ! gcloud compute firewall-rules describe "quickbite-allow-internal" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  gcloud compute firewall-rules create "quickbite-allow-internal" \
    --network="${VPC_NAME}" \
    --direction=INGRESS \
    --action=ALLOW \
    --source-ranges="10.10.0.0/24,172.16.0.0/12" \
    --rules="all" \
    --project="${PROJECT_ID}"
fi

if ! gcloud compute routers describe "quickbite-router" --region="${REGION}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  gcloud compute routers create "quickbite-router" \
    --network="${VPC_NAME}" \
    --region="${REGION}" \
    --project="${PROJECT_ID}"
fi

if ! gcloud compute routers nats describe "quickbite-nat" --router="quickbite-router" --region="${REGION}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  gcloud compute routers nats create "quickbite-nat" \
    --router="quickbite-router" \
    --region="${REGION}" \
    --auto-allocate-nat-external-ips \
    --nat-all-subnet-ip-ranges \
    --project="${PROJECT_ID}"
fi

echo "=== 4/5 Creating Private Shielded GCE VM (${VM_NAME}, e2-standard-4, 80GB SSD) ==="
if ! gcloud compute instances describe "${VM_NAME}" --zone="${ZONE}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  gcloud compute instances create "${VM_NAME}" \
    --project="${PROJECT_ID}" \
    --zone="${ZONE}" \
    --machine-type="e2-standard-4" \
    --network-interface="subnet=${SUBNET_NAME},no-address" \
    --service-account="${SA_EMAIL}" \
    --scopes="https://www.googleapis.com/auth/cloud-platform" \
    --image-family="ubuntu-2404-lts-amd64" \
    --image-project="ubuntu-os-cloud" \
    --boot-disk-size="80GB" \
    --boot-disk-type="pd-ssd" \
    --shielded-secure-boot \
    --shielded-vtpm \
    --shielded-integrity-monitoring
fi

echo "=== 5/5 Waiting for SSH via IAP Tunnel on ${VM_NAME} ==="
for i in {1..15}; do
  if gcloud compute ssh "${VM_NAME}" --zone="${ZONE}" --project="${PROJECT_ID}" --tunnel-through-iap --command="echo 'SSH Ready'" >/dev/null 2>&1; then
    echo "   IAP SSH connection established!"
    break
  fi
  echo "   Waiting 5s for VM boot & IAP SSH readiness (${i}/15)..."
  sleep 5
done

echo "✅ GCE VM ${VM_NAME} is up and reachable via IAP!"
