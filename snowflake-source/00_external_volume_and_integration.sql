-- =============================================================================
-- UrbanFork Snowflake Source Setup — Step 0: Warehouses, DB & GCS Integrations
-- Placeholders {{GCS_LAKEHOUSE_BUCKET}} are rendered by seed_snowflake_instance.py
-- =============================================================================
USE ROLE ACCOUNTADMIN;

-- Tighten Snowflake's default COMPUTE_WH from 600s (10 min) down to 60s
ALTER WAREHOUSE IF EXISTS COMPUTE_WH SET AUTO_SUSPEND = 60;

CREATE WAREHOUSE IF NOT EXISTS UF_LOAD_WH
    WAREHOUSE_SIZE = 'XSMALL'
    AUTO_SUSPEND = 60
    AUTO_RESUME = TRUE
    INITIALLY_SUSPENDED = TRUE;

CREATE WAREHOUSE IF NOT EXISTS UF_TRANSFORM_WH
    WAREHOUSE_SIZE = 'XSMALL'
    AUTO_SUSPEND = 60
    AUTO_RESUME = TRUE
    INITIALLY_SUSPENDED = TRUE;

CREATE DATABASE IF NOT EXISTS URBANFORK_PROD;
CREATE SCHEMA IF NOT EXISTS URBANFORK_PROD.OPS_RAW;
CREATE SCHEMA IF NOT EXISTS URBANFORK_PROD.IOT_RAW;
CREATE SCHEMA IF NOT EXISTS URBANFORK_PROD.MART;
CREATE SCHEMA IF NOT EXISTS URBANFORK_PROD.GOVERNANCE;

-- 1. External Volume on Google Cloud Storage for Snowflake-Managed Iceberg Tables
CREATE OR REPLACE EXTERNAL VOLUME URBANFORK_GCS_ICEBERG_VOL
    STORAGE_LOCATIONS = (
        (
            NAME = 'urbanfork-gcs-us-central1'
            STORAGE_PROVIDER = 'GCS'
            STORAGE_BASE_URL = 'gcs://{{GCS_LAKEHOUSE_BUCKET}}/iceberg/'
        )
    )
    ALLOW_WRITES = TRUE;

-- 2. Storage Integration on Google Cloud Storage for Parquet Unload & External Stages
CREATE OR REPLACE STORAGE INTEGRATION URBANFORK_GCS_INT
    TYPE = EXTERNAL_STAGE
    STORAGE_PROVIDER = 'GCS'
    ENABLED = TRUE
    STORAGE_ALLOWED_LOCATIONS = ('gcs://{{GCS_LAKEHOUSE_BUCKET}}/');

-- Inspect generated GCP Service Account(s) to grant roles/storage.objectAdmin on GCS:
DESC EXTERNAL VOLUME URBANFORK_GCS_ICEBERG_VOL;
DESC STORAGE INTEGRATION URBANFORK_GCS_INT;
