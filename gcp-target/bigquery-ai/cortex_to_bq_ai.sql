-- =============================================================================
-- QuickBite BigQuery AI Migration (Act 3B)
-- Migrated from Snowflake Cortex AISQL & SNOWFLAKE.ML.FORECAST:
--   1. AI_CLASSIFY + AI_SENTIMENT -> Zero-shot BigQuery AI.CLASSIFY & AI.SCORE
--      (NO CREATE MODEL required; uses Gemini 2.5 Flash natively inside SQL!)
--   2. SNOWFLAKE.ML.FORECAST      -> Zero-shot BigQuery AI.FORECAST (TimesFM 2.5)
--      (Replaces 3-step CREATE MODEL + CALL FORECAST + RESULT_SCAN with 1 query!)
-- =============================================================================

-- 1. Triage recent customer support dispute tickets using BigQuery AI.CLASSIFY & AI.SCORE
CREATE OR REPLACE TABLE `dcd-migration-demo.quickbite_gold_mart.BQ_AI_DISPUTE_TRIAGE` AS
WITH recent_tickets AS (
  SELECT
    DSP_ID,
    ORD_ID,
    DSP_TS,
    RFND_AMT_USD,
    DSP_RSN_CD,
    CUST_TICKET_TXT
  FROM `dcd-migration-demo.quickbite_raw_ops.DSP_REFUND_FCT`
  WHERE CUST_TICKET_TXT IS NOT NULL
  ORDER BY DSP_TS DESC
  LIMIT 30
)
SELECT
  DSP_ID,
  ORD_ID,
  DSP_TS,
  RFND_AMT_USD,
  DSP_RSN_CD,
  CUST_TICKET_TXT,
  AI.CLASSIFY(
    CUST_TICKET_TXT,
    categories => [
      'Missing Item',
      'Cold or Spilled Food',
      'Late Courier',
      'Suspected Refund Abuse'
    ]
  ) AS BQ_AI_PREDICTED_CATEGORY,
  ROUND(
    AI.SCORE(
      (CUST_TICKET_TXT, 'Customer anger and complaint urgency severity for a food delivery refund ticket')
    ),
    3
  ) AS BQ_AI_URGENCY_SCORE
FROM recent_tickets;

-- 2. Zero-Shot 14-Day Regional Order Forecast using TimesFM 2.5 (Replaces SNOWFLAKE.ML.FORECAST!)
CREATE OR REPLACE TABLE `dcd-migration-demo.quickbite_gold_mart.FCT_REGIONAL_ORDER_FORECAST_14D` AS
SELECT
  REG_CD,
  forecast_timestamp AS FORECAST_DAY_TS,
  ROUND(forecast_value, 2) AS FORECAST_ORDERS_CNT,
  ROUND(prediction_interval_lower_bound, 2) AS LOWER_BOUND_95,
  ROUND(prediction_interval_upper_bound, 2) AS UPPER_BOUND_95,
  confidence_level,
  ai_forecast_status
FROM AI.FORECAST(
  (
    SELECT
      TIMESTAMP(DATE(h.ORD_TS)) AS ORD_DAY_TS,
      z.REG_CD,
      CAST(COUNT(*) AS FLOAT64) AS DAILY_ORDERS_CNT
    FROM `dcd-migration-demo.quickbite_raw_ops.DLV_ORD_HDR` h
    JOIN `dcd-migration-demo.quickbite_raw_ops.GEO_ZONE_LKP` z
      ON h.ZONE_ID = z.ZONE_ID
    WHERE h.ORD_STS_CD = 'D'
      AND DATE(h.ORD_TS) BETWEEN '2025-06-01' AND '2026-03-31'
    GROUP BY 1, 2
  ),
  data_col => 'DAILY_ORDERS_CNT',
  timestamp_col => 'ORD_DAY_TS',
  id_cols => ['REG_CD'],
  horizon => 14,
  model => 'TimesFM 2.5',
  confidence_level => 0.95
);
