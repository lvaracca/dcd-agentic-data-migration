variable "airbyte_server_url" {
  type        = string
  default     = "http://localhost:8000/api/public/v1"
  description = "Airbyte API URL (local abctl or Airbyte Cloud)"
}

variable "airbyte_api_token" {
  type      = string
  sensitive = true
}

variable "airbyte_workspace_id" {
  type = string
}

variable "postgres_host" {
  type        = string
  default     = "host.docker.internal"
  description = "Hostname for urbanfork-oltp-postgres reachable from Airbyte"
}

variable "postgres_password" {
  type      = string
  sensitive = true
  default   = "uf_demo_password"
}

variable "snowflake_account" {
  type = string
}

variable "snowflake_user" {
  type = string
}

variable "snowflake_password" {
  type      = string
  sensitive = true
}

variable "gcp_project_id" {
  type    = string
  default = ""
}

variable "gcp_region" {
  type        = string
  default     = "us-central1"
  description = "BigQuery dataset location and GCP region"
}

variable "bq_raw_dataset" {
  type        = string
  default     = "urbanfork_raw_ops"
  description = "Target BigQuery raw dataset for Airbyte incremental sync"
}

variable "gcs_lakehouse_bucket" {
  type    = string
  default = ""
}
