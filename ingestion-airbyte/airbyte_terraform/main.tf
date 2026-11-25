# ==============================================================================
# Declarative Airbyte Pipeline Configuration (Pre-Migration State: Snowflake)
# ------------------------------------------------------------------------------
# DEMO ACT 2 (Seamless Ingestion Cutover):
# Antigravity inspects this Terraform configuration, adds an
# `airbyte_destination_bigquery` resource (using GCS staging in `us-central1`),
# and switches `airbyte_connection.urbanfork_oltp_incremental` from Snowflake
# to BigQuery while preserving exact stream names, primary keys, and the
# `updated_at` incremental cursor!
# ==============================================================================
terraform {
  required_providers {
    airbyte = {
      source  = "airbytehq/airbyte"
      version = "~> 0.6.0"
    }
  }
}

provider "airbyte" {
  server_url = var.airbyte_server_url # Default abctl local: http://localhost:8000/api/public/v1
  bearer_auth = var.airbyte_api_token
}

resource "airbyte_source_postgres" "urbanfork_oltp" {
  name         = "UrbanFork OLTP Production (PostgreSQL)"
  workspace_id = var.airbyte_workspace_id
  configuration = {
    host     = var.postgres_host
    port     = 5439
    database = "urbanfork_oltp"
    schemas  = ["oltp"]
    username = "uf_airbyte_user"
    password = var.postgres_password
    ssl_mode = { disable = {} }
    replication_method = {
      scan_changes_with_user_defined_cursor = {}
    }
  }
}

# LEGACY DESTINATION: Snowflake URBANFORK_PROD.OPS_RAW (DECOMMISSIONED IN ACT 2)
resource "airbyte_destination_snowflake" "snowflake_ops_raw" {
  name         = "Snowflake - URBANFORK_PROD (Legacy)"
  workspace_id = var.airbyte_workspace_id
  configuration = {
    host      = "${var.snowflake_account}.snowflakecomputing.com"
    role      = "ACCOUNTADMIN"
    warehouse = "UF_LOAD_WH"
    database  = "URBANFORK_PROD"
    schema    = "OPS_RAW"
    username  = var.snowflake_user
    credentials = {
      username_and_password = {
        password = var.snowflake_password
      }
    }
  }
}

# TARGET DESTINATION: Google BigQuery (Keyless GCE Service Account ADC)
resource "airbyte_destination_bigquery" "bigquery_raw_ops" {
  name         = "Google BigQuery - UrbanFork Lakehouse"
  workspace_id = var.airbyte_workspace_id
  configuration = {
    project_id       = var.gcp_project_id
    dataset_id       = var.bq_raw_dataset
    dataset_location = var.gcp_region
    loading_method = {
      batched_standard_inserts = {}
    }
  }
}

# ACTIVE INCREMENTAL CONNECTION (Cut over from Snowflake -> BigQuery!)
resource "airbyte_connection" "urbanfork_oltp_incremental" {
  name                 = "UrbanFork OLTP -> Warehouse Incremental Sync"
  source_id            = airbyte_source_postgres.urbanfork_oltp.source_id
  destination_id       = airbyte_destination_bigquery.bigquery_raw_ops.destination_id
  namespace_definition = "destination"
  prefix               = "CDC_"

  schedule = {
    schedule_type   = "cron"
    cron_expression = "0 0/15 * * * ?"
  }

  configurations = {
    streams = [
      {
        name         = "dlv_ord_hdr"
        sync_mode    = "incremental_deduped_history"
        cursor_field = ["updated_at"]
        primary_key  = [["ord_id"]]
      },
      {
        name         = "dlv_ord_item_ln"
        sync_mode    = "incremental_deduped_history"
        cursor_field = ["updated_at"]
        primary_key  = [["ord_ln_id"]]
      },
      {
        name         = "dsp_refund_fct"
        sync_mode    = "incremental_deduped_history"
        cursor_field = ["updated_at"]
        primary_key  = [["dsp_id"]]
      }
    ]
  }
}
