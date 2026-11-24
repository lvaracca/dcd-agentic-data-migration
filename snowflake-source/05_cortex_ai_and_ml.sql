-- =============================================================================
-- QuickBite Snowflake Source Setup — Step 5: Snowflake Cortex AISQL & ML Forecast
-- Migrated by Antigravity to BigQuery AI:
--   * AI_CLASSIFY           -> BigQuery AI.CLASSIFY (zero-shot)
--   * AI_SENTIMENT          -> BigQuery AI.SCORE (calibrated severity 0.0-1.0)
--   * SNOWFLAKE.ML.FORECAST -> BigQuery AI.FORECAST (zero-shot TimesFM, no training!)
-- =============================================================================
USE ROLE ACCOUNTADMIN;
USE WAREHOUSE QB_TRANSFORM_WH;
USE DATABASE QUICKBITE_PROD;

-- 1. Triage recent customer support dispute tickets using Snowflake Cortex AISQL
CREATE OR REPLACE TABLE MART.CORTEX_DISPUTE_TRIAGE_SAMPLE AS
SELECT
    d.DSP_ID,
    d.ORD_ID,
    d.DSP_TS,
    d.RFND_AMT_USD,
    d.DSP_RSN_CD,
    d.CUST_TICKET_TXT,
    AI_SENTIMENT(d.CUST_TICKET_TXT):categories[0]:sentiment::VARCHAR AS CORTEX_SENTIMENT_LABEL,
    AI_CLASSIFY(
        d.CUST_TICKET_TXT,
        ['Missing Item', 'Cold or Spilled Food', 'Late Courier', 'Suspected Refund Abuse']
    ):labels[0]::VARCHAR AS CORTEX_PREDICTED_CATEGORY
FROM (
    SELECT *
    FROM OPS_RAW.DSP_REFUND_FCT
    ORDER BY DSP_TS DESC
    LIMIT 100
) d;

-- 2. Train & execute a Snowflake ML Forecast model on Daily Regional Order Volume
CREATE OR REPLACE TABLE MART.FCT_DAILY_REGION_DEMAND_TRAIN AS
SELECT
    CAST(DATE_TRUNC('day', h.ORD_TS) AS TIMESTAMP_NTZ) AS ORD_DAY_TS,
    z.REG_CD,
    CAST(COUNT(*) AS FLOAT) AS DAILY_ORDERS_CNT
FROM OPS_RAW.DLV_ORD_HDR h
JOIN OPS_RAW.GEO_ZONE_LKP z ON h.ZONE_ID = z.ZONE_ID
WHERE h.ORD_STS_CD = 'D'
  AND TO_DATE(h.ORD_TS) BETWEEN '2025-06-01' AND '2026-03-31'
GROUP BY 1, 2;

CREATE OR REPLACE SNOWFLAKE.ML.FORECAST MART.MDL_REGIONAL_ORDER_FORECAST (
    INPUT_DATA => SYSTEM$REFERENCE('TABLE', 'QUICKBITE_PROD.MART.FCT_DAILY_REGION_DEMAND_TRAIN'),
    SERIES_COLNAME => 'REG_CD',
    TIMESTAMP_COLNAME => 'ORD_DAY_TS',
    TARGET_COLNAME => 'DAILY_ORDERS_CNT'
);

CALL MART.MDL_REGIONAL_ORDER_FORECAST!FORECAST(FORECASTING_PERIODS => 14);

CREATE OR REPLACE TABLE MART.FCT_REGIONAL_ORDER_FORECAST_14D AS
SELECT * FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()));
