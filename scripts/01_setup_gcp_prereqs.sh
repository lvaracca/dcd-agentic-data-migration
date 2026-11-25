#!/usr/bin/env bash
# ==============================================================================
# UrbanFork Demo — Step 1: Google Cloud Bucket & BigLake Setup (us-central1)
# Usage:
#   1. Initial setup (Bucket + BigLake Connection + APIs):
#      ./scripts/01_setup_gcp_prereqs.sh
#   2. Bind Snowflake GCP Service Account (printed by seed_snowflake_instance.py --step 1):
#      ./scripts/01_setup_gcp_prereqs.sh --grant-snowflake-sa <SNOWFLAKE_GCP_SA_EMAIL>
# ==============================================================================
set -euo pipefail

if [[ -f .env ]]; then
  set -a
  source .env
  set +a
fi

export CLOUDSDK_METRICS_ENVIRONMENT="${CLOUDSDK_METRICS_ENVIRONMENT:+$CLOUDSDK_METRICS_ENVIRONMENT }datacloud.antigravity"

PROJECT_ID="${GCP_PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}"
REGION="${GCP_REGION:-us-central1}"
BUCKET_NAME="${GCS_LAKEHOUSE_BUCKET:-${PROJECT_ID}-urbanfork-lakehouse}"
BIGLAKE_CONN="${BQ_BIGLAKE_CONNECTION:-biglake-iceberg-conn}"

if [[ -z "${PROJECT_ID}" || "${PROJECT_ID}" == "your-gcp-project-id" ]]; then
  echo "ERROR: Set GCP_PROJECT_ID in .env or via 'gcloud config set project <PROJECT_ID>'."
  exit 1
fi

if [[ "${1:-}" == "--grant-snowflake-sa" ]]; then
  SF_SA="${2:-}"
  if [[ -z "${SF_SA}" ]]; then
    echo "Usage: $0 --grant-snowflake-sa <SNOWFLAKE_GCP_SERVICE_ACCOUNT_EMAIL>"
    exit 1
  fi
  echo "Granting roles/storage.objectAdmin & roles/storage.legacyBucketReader on gs://${BUCKET_NAME} to Snowflake SA: ${SF_SA}..."
  gcloud storage buckets add-iam-policy-binding "gs://${BUCKET_NAME}" \
    --member="serviceAccount:${SF_SA}" \
    --role="roles/storage.objectAdmin" \
    --project="${PROJECT_ID}"
  gcloud storage buckets add-iam-policy-binding "gs://${BUCKET_NAME}" \
    --member="serviceAccount:${SF_SA}" \
    --role="roles/storage.legacyBucketReader" \
    --project="${PROJECT_ID}"
  echo "Done! Snowflake can now read/write Iceberg & Parquet files in gs://${BUCKET_NAME}."
  exit 0
fi

echo "=== Configuring GCP Project: ${PROJECT_ID} (Region: ${REGION}) ==="
gcloud services enable \
  bigquery.googleapis.com \
  biglake.googleapis.com \
  bigqueryconnection.googleapis.com \
  dataplex.googleapis.com \
  dataform.googleapis.com \
  dataproc.googleapis.com \
  datacatalog.googleapis.com \
  aiplatform.googleapis.com \
  geminidataanalytics.googleapis.com \
  storage.googleapis.com \
  --project="${PROJECT_ID}"

echo "=== Creating Lakehouse Bucket: gs://${BUCKET_NAME} in ${REGION} ==="
if ! gcloud storage buckets describe "gs://${BUCKET_NAME}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  gcloud storage buckets create "gs://${BUCKET_NAME}" \
    --project="${PROJECT_ID}" \
    --location="${REGION}" \
    --uniform-bucket-level-access
else
  echo "Bucket gs://${BUCKET_NAME} already exists."
fi

echo "=== Creating BigLake Connection: ${BIGLAKE_CONN} in ${REGION} ==="
if ! bq show --connection --location="${REGION}" --project_id="${PROJECT_ID}" "${BIGLAKE_CONN}" >/dev/null 2>&1; then
  bq mk --connection \
    --connection_type=CLOUD_RESOURCE \
    --location="${REGION}" \
    --project_id="${PROJECT_ID}" \
    "${BIGLAKE_CONN}"
fi

BQ_CONN_SA=$(bq show --connection --format=json --location="${REGION}" --project_id="${PROJECT_ID}" "${BIGLAKE_CONN}" | python3 -c "import sys, json; print(json.load(sys.stdin)['cloudResource']['serviceAccountId'])")
echo "Granting BigLake SA (${BQ_CONN_SA}) access to gs://${BUCKET_NAME}..."
for attempt in 1 2 3 4 5; do
  if gcloud storage buckets add-iam-policy-binding "gs://${BUCKET_NAME}" \
    --member="serviceAccount:${BQ_CONN_SA}" \
    --role="roles/storage.objectAdmin" \
    --project="${PROJECT_ID}" 2>/dev/null; then
    break
  fi
  echo "  Waiting 5s for new BigLake Service Account IAM propagation (attempt ${attempt}/5)..."
  sleep 5
done

gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${BQ_CONN_SA}" \
  --role="roles/aiplatform.user" \
  --condition=None >/dev/null

echo "=== Creating Target BigQuery Datasets in ${REGION} ==="
for DS in "${BQ_RAW_DATASET:-urbanfork_raw_ops}" "${BQ_IOT_DATASET:-urbanfork_raw_iot}" "${BQ_MART_DATASET:-urbanfork_gold_mart}"; do
  if ! bq --project_id="${PROJECT_ID}" ls -d "${DS}" >/dev/null 2>&1; then
    bq --location="${REGION}" --project_id="${PROJECT_ID}" mk --dataset --label=datacloud:antigravity "${PROJECT_ID}:${DS}"
  fi
done

echo ""
echo "✅ GCP Prerequisites ready in ${REGION}!"
echo "   Bucket:             gs://${BUCKET_NAME}"
echo "   BigLake Connection: ${PROJECT_ID}.${REGION}.${BIGLAKE_CONN}"
echo "Next step: Configure .env with your Snowflake 30-day Trial credentials and run:"
echo "   .venv/bin/python data-generator/seed_snowflake_instance.py --step 1"
