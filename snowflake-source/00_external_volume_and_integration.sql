-- =============================================================================
-- QuickBite Snowflake Source Setup — Step 0: Warehouses, DB & GCS Integrations
-- Placeholders {{GCS_LAKEHOUSE_BUCKET}} are rendered by seed_snowflake_instance.py
-- =============================================================================
USE ROLE ACCOUNTADMIN;

-- Tighten Snowflake's default COMPUTE_WH from 600s (10 min) down to 60s
ALTER WAREHOUSE IF EXISTS COMPUTE_WH SET AUTO_SUSPEND = 60;

CREATE WAREHOUSE IF NOT EXISTS QB_LOAD_WH
    WAREHOUSE_SIZE = 'XSMALL'
    AUTO_SUSPEND = 60
    AUTO_RESUME = TRUE
    INITIALLY_SUSPENDED = TRUE;

CREATE WAREHOUSE IF NOT EXISTS QB_TRANSFORM_WH
    WAREHOUSE_SIZE = 'XSMALL'
    AUTO_SUSPEND = 60
    AUTO_RESUME = TRUE
    INITIALLY_SUSPENDED = TRUE;

CREATE DATABASE IF NOT EXISTS QUICKBITE_PROD;
CREATE SCHEMA IF NOT EXISTS QUICKBITE_PROD.OPS_RAW;
CREATE SCHEMA IF NOT EXISTS QUICKBITE_PROD.IOT_RAW;
CREATE SCHEMA IF NOT EXISTS QUICKBITE_PROD.MART;
CREATE SCHEMA IF NOT EXISTS QUICKBITE_PROD.GOVERNANCE;

-- 1. External Volume on Google Cloud Storage for Snowflake-Managed Iceberg Tables
CREATE OR REPLACE EXTERNAL VOLUME QUICKBITE_GCS_ICEBERG_VOL
    STORAGE_LOCATIONS = (
        (
            NAME = 'quickbite-gcs-us-central1'
            STORAGE_PROVIDER = 'GCS'
            STORAGE_BASE_URL = 'gcs://{{GCS_LAKEHOUSE_BUCKET}}/iceberg/'
        )
    )
    ALLOW_WRITES = TRUE;

-- 2. Storage Integration on Google Cloud Storage for Parquet Unload & External Stages
CREATE OR REPLACE STORAGE INTEGRATION QUICKBITE_GCS_INT
    TYPE = EXTERNAL_STAGE
    STORAGE_PROVIDER = 'GCS'
    ENABLED = TRUE
    STORAGE_ALLOWED_LOCATIONS = ('gcs://{{GCS_LAKEHOUSE_BUCKET}}/');

-- Inspect generated GCP Service Account(s) to grant roles/storage.objectAdmin on GCS:
DESC EXTERNAL VOLUME QUICKBITE_GCS_ICEBERG_VOL;
DESC STORAGE INTEGRATION QUICKBITE_GCS_INT;
