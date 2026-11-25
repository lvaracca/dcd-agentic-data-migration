-- =============================================================================
-- UrbanFork Snowflake Source Setup — Step 4: Legacy Business Views & Scripting
-- CRITICAL DEMO ASSET:
-- All core UrbanFork business rules ("Golden Math") are hardcoded inside these
-- Snowflake SQL objects rather than documented in a catalog! Antigravity
-- translates them to Dataform AND extracts their business semantics into OKF
-- and Knowledge Catalog.
-- =============================================================================
USE ROLE ACCOUNTADMIN;
USE WAREHOUSE UF_TRANSFORM_WH;
USE DATABASE URBANFORK_PROD;

-- -----------------------------------------------------------------------------
-- View 1: Platform Net Revenue (Net Take) & Effective Take-Rate %
-- Encodes:
--   * VERT_CD: 1 = Restaurant Hot Food, 2 = Quick-Commerce Grocery
--   * ORD_STS_CD: 'D' = Delivered (realized), 'C' = Cancelled, 'R' = Rejected, 'P' = In-Prep
--   * Anti-Fanout CTE: Pre-aggregates basket GMV and Approved Refunds (RFND_STS_FLG = 1)
--     separately before joining on ORD_ID
--   * SCD Type 2 Commission Lookup: Joins CAL_DT BETWEEN EFF_FROM_DT AND EFF_TO_DT
--   * Excludes Courier Tips (TIP_USD passes 100% to couriers, never counted in Net Revenue!)
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW MART.VW_PLATFORM_NET_REVENUE AS
WITH basket_gmv AS (
    SELECT
        ORD_ID,
        SUM(QTY_N * UNIT_PRC_USD) AS GMV_USD,
        SUM(QTY_N) AS TOTAL_ITEMS_N
    FROM OPS_RAW.DLV_ORD_ITEM_LN
    GROUP BY ORD_ID
),
approved_refunds AS (
    SELECT
        ORD_ID,
        SUM(RFND_AMT_USD) AS APPROVED_REFUND_USD,
        COUNT_IF(DSP_RSN_CD IN (1, 2)) AS QUALITY_DISPUTE_CNT
    FROM OPS_RAW.DSP_REFUND_FCT
    WHERE RFND_STS_FLG = 1
    GROUP BY ORD_ID
)
SELECT
    cal.CAL_DT,
    cal.FISC_YR_N,
    cal.FISC_QTR_N,
    z.REG_CD,
    z.CITY_NM,
    h.ZONE_ID,
    h.VERT_CD,
    IFF(h.VERT_CD = 1, 'Restaurant', 'Grocery') AS VERTICAL_NM,
    COUNT(DISTINCT h.ORD_ID) AS COMPLETED_ORDERS_CNT,
    SUM(b.GMV_USD) AS GROSS_MERCHANDISE_VALUE_USD,
    SUM(ROUND(b.GMV_USD * scd.COMM_RATE_PCT, 2)) AS MERCHANT_COMMISSION_REV_USD,
    SUM(h.DLV_FEE_USD + h.SRV_FEE_USD) AS CUSTOMER_FEES_REV_USD,
    SUM(h.CRR_PAY_USD) AS COURIER_COST_USD,
    SUM(h.PROMO_VOUCHER_USD) AS PROMO_SUBSIDY_USD,
    SUM(ZEROIFNULL(r.APPROVED_REFUND_USD)) AS APPROVED_REFUNDS_USD,
    SUM(
        ROUND(b.GMV_USD * scd.COMM_RATE_PCT, 2)
        + h.DLV_FEE_USD
        + h.SRV_FEE_USD
        - h.CRR_PAY_USD
        - h.PROMO_VOUCHER_USD
        - ZEROIFNULL(r.APPROVED_REFUND_USD)
    ) AS PLATFORM_NET_REVENUE_USD,
    ROUND(
        SUM(
            ROUND(b.GMV_USD * scd.COMM_RATE_PCT, 2)
            + h.DLV_FEE_USD
            + h.SRV_FEE_USD
            - h.CRR_PAY_USD
            - h.PROMO_VOUCHER_USD
            - ZEROIFNULL(r.APPROVED_REFUND_USD)
        ) / NULLIF(SUM(b.GMV_USD), 0),
        4
    ) AS EFFECTIVE_TAKE_RATE_PCT
FROM OPS_RAW.DLV_ORD_HDR h
JOIN OPS_RAW.SYS_CAL_DIM cal
    ON h.ORD_DT_SK = cal.DT_SK
JOIN OPS_RAW.GEO_ZONE_LKP z
    ON h.ZONE_ID = z.ZONE_ID
JOIN basket_gmv b
    ON h.ORD_ID = b.ORD_ID
JOIN OPS_RAW.MRC_COMM_SCD2 scd
    ON h.MRC_ID = scd.MRC_ID
   AND cal.CAL_DT BETWEEN scd.EFF_FROM_DT AND scd.EFF_TO_DT
LEFT JOIN approved_refunds r
    ON h.ORD_ID = r.ORD_ID
WHERE h.ORD_STS_CD = 'D'
GROUP BY 1, 2, 3, 4, 5, 6, 7, 8;

-- -----------------------------------------------------------------------------
-- View 2: Delivery SLA Telemetry (Semi-Structured VARIANT + FLATTEN + ASOF JOIN)
-- Encodes:
--   * Extraction of JSON metrics (prep_sec, travel_sec, eta_sec, anomaly_flags)
--   * Mandatory exclusion of app_ver = '3.8.0-beta' (GPS timer overflow bug!)
--   * SLA Breach = (prep_sec + travel_sec) > SLA_TARGET_MIN * 60
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW MART.VW_DELIVERY_SLA_TELEMETRY AS
WITH dedup_delivered_pings AS (
    SELECT
        p.ORD_ID,
        p.INGEST_TS,
        p.PAYLOAD:app_ver::VARCHAR AS APP_VER,
        TRY_TO_NUMBER(p.PAYLOAD:metrics.prep_sec::VARCHAR) AS KITCHEN_PREP_SEC,
        TRY_TO_NUMBER(p.PAYLOAD:metrics.travel_sec::VARCHAR) AS COURIER_TRAVEL_SEC,
        TRY_TO_NUMBER(p.PAYLOAD:metrics.eta_sec::VARCHAR) AS QUOTED_ETA_SEC,
        ARRAY_SIZE(p.PAYLOAD:anomaly_flags) AS ANOMALY_FLAG_CNT
    FROM IOT_RAW.APP_DELIVERY_PINGS p
    WHERE p.PAYLOAD:stage::VARCHAR = 'DELIVERED'
      AND p.PAYLOAD:app_ver::VARCHAR != '3.8.0-beta'
    QUALIFY ROW_NUMBER() OVER (PARTITION BY p.ORD_ID ORDER BY p.INGEST_TS DESC) = 1
),
flattened_flags AS (
    SELECT
        p.ORD_ID,
        LISTAGG(DISTINCT f.VALUE::VARCHAR, ',') WITHIN GROUP (ORDER BY f.VALUE::VARCHAR) AS ANOMALY_FLAGS_CSV
    FROM IOT_RAW.APP_DELIVERY_PINGS p,
    LATERAL FLATTEN(input => p.PAYLOAD:anomaly_flags, OUTER => FALSE) f
    WHERE p.PAYLOAD:app_ver::VARCHAR != '3.8.0-beta'
    GROUP BY p.ORD_ID
)
SELECT
    h.MRC_ID,
    h.ZONE_ID,
    z.CITY_NM,
    z.REG_CD,
    DATE_TRUNC('day', h.ORD_TS) AS ORD_DAY,
    COUNT(DISTINCT h.ORD_ID) AS MEASURED_ORDERS_CNT,
    ROUND(AVG(lp.KITCHEN_PREP_SEC / 60.0), 2) AS AVG_KITCHEN_PREP_MIN,
    ROUND(AVG((lp.KITCHEN_PREP_SEC + lp.COURIER_TRAVEL_SEC) / 60.0), 2) AS AVG_TOTAL_DELIVERY_MIN,
    COUNT_IF((lp.KITCHEN_PREP_SEC + lp.COURIER_TRAVEL_SEC) > z.SLA_TARGET_MIN * 60) AS SLA_BREACH_CNT,
    ROUND(
        COUNT_IF((lp.KITCHEN_PREP_SEC + lp.COURIER_TRAVEL_SEC) > z.SLA_TARGET_MIN * 60)
        / NULLIF(COUNT(DISTINCT h.ORD_ID), 0),
        4
    ) AS SLA_BREACH_RATE,
    COUNT(DISTINCT d.DSP_ID) AS POST_DELIVERY_DISPUTE_CNT,
    COUNT_IF(ff.ANOMALY_FLAGS_CSV LIKE '%SLA_EXCEEDED%') AS TELEMETRY_FLAGGED_SLA_CNT
FROM OPS_RAW.DLV_ORD_HDR h
JOIN OPS_RAW.GEO_ZONE_LKP z
    ON h.ZONE_ID = z.ZONE_ID
JOIN dedup_delivered_pings lp
    ON h.ORD_ID = lp.ORD_ID
LEFT JOIN flattened_flags ff
    ON h.ORD_ID = ff.ORD_ID
ASOF JOIN OPS_RAW.DSP_REFUND_FCT d
    MATCH_CONDITION (lp.INGEST_TS <= d.DSP_TS)
    ON h.ORD_ID = d.ORD_ID
WHERE h.ORD_STS_CD = 'D'
GROUP BY 1, 2, 3, 4, 5;

-- -----------------------------------------------------------------------------
-- View 3: Prime Partner Merchant Tiering Scorecard
-- Encodes the 4-condition corporate definition of "Prime Partner" over trailing 90d
-- relative to max dataset date (2026-03-31):
--   1. Trailing 90d Completed GMV > $25,000
--   2. Average Kitchen Prep Time < 14.0 minutes (excluding app_ver '3.8.0-beta')
--   3. Quality Dispute Rate (DSP_RSN_CD IN (1=Missing Item, 2=Cold/Spilled)) < 2.0%
--   4. Merchant Order Rejection Rate (ORD_STS_CD = 'R') < 1.0%
-- Also joins Merchant Chargebacks via implicit key 'CBK-' || ORD_ID = REF_DOC_TXT
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW MART.VW_PRIME_PARTNER_SCORECARD AS
WITH max_dt_anchor AS (
    SELECT MAX(TO_DATE(ORD_TS)) AS ANCHOR_DT FROM OPS_RAW.DLV_ORD_HDR
),
ord_90d AS (
    SELECT
        h.MRC_ID,
        h.ORD_ID,
        h.ORD_STS_CD
    FROM OPS_RAW.DLV_ORD_HDR h
    CROSS JOIN max_dt_anchor a
    WHERE TO_DATE(h.ORD_TS) > DATEADD('day', -90, a.ANCHOR_DT)
),
gmv_90d AS (
    SELECT
        o.MRC_ID,
        SUM(IFF(o.ORD_STS_CD = 'D', ln.QTY_N * ln.UNIT_PRC_USD, 0)) AS TRAILING_90D_GMV_USD
    FROM ord_90d o
    LEFT JOIN OPS_RAW.DLV_ORD_ITEM_LN ln ON o.ORD_ID = ln.ORD_ID
    GROUP BY o.MRC_ID
),
prep_90d AS (
    SELECT
        o.MRC_ID,
        AVG(TRY_TO_NUMBER(p.PAYLOAD:metrics.prep_sec::VARCHAR) / 60.0) AS AVG_PREP_MIN_90D
    FROM ord_90d o
    JOIN IOT_RAW.APP_DELIVERY_PINGS p ON o.ORD_ID = p.ORD_ID
    WHERE o.ORD_STS_CD = 'D'
      AND p.PAYLOAD:stage::VARCHAR = 'DELIVERED'
      AND p.PAYLOAD:app_ver::VARCHAR != '3.8.0-beta'
    GROUP BY o.MRC_ID
),
disputes_and_cbk_90d AS (
    SELECT
        o.MRC_ID,
        COUNT(DISTINCT IFF(d.DSP_RSN_CD IN (1, 2) AND d.RFND_STS_FLG = 1, o.ORD_ID, NULL)) AS QUALITY_DISPUTE_ORDERS_CNT,
        ZEROIFNULL(SUM(ABS(led.LEDGER_AMT_USD))) AS TOTAL_CHARGEBACK_USD
    FROM ord_90d o
    LEFT JOIN OPS_RAW.DSP_REFUND_FCT d
        ON o.ORD_ID = d.ORD_ID
    LEFT JOIN OPS_RAW.MRC_PAYOUT_LEDGER led
        ON CONCAT('CBK-', o.ORD_ID) = led.REF_DOC_TXT
    WHERE o.ORD_STS_CD = 'D'
    GROUP BY o.MRC_ID
),
order_counts_90d AS (
    SELECT
        MRC_ID,
        COUNT(*) AS TOTAL_ORDERS_90D,
        COUNT_IF(ORD_STS_CD = 'D') AS DELIVERED_ORDERS_90D,
        COUNT_IF(ORD_STS_CD = 'R') AS REJECTED_ORDERS_90D
    FROM ord_90d
    GROUP BY MRC_ID
)
SELECT
    m.MRC_ID,
    m.MRC_NM,
    IFF(m.VERT_CD = 1, 'Restaurant', 'Grocery') AS VERTICAL_NM,
    m.CUISINE_CAT,
    z.ZONE_ID,
    z.CITY_NM,
    z.REG_CD,
    ZEROIFNULL(g.TRAILING_90D_GMV_USD) AS TRAILING_90D_GMV_USD,
    oc.DELIVERED_ORDERS_90D,
    ROUND(p.AVG_PREP_MIN_90D, 2) AS AVG_PREP_MIN_90D,
    ROUND(ZEROIFNULL(dc.QUALITY_DISPUTE_ORDERS_CNT) / NULLIF(oc.DELIVERED_ORDERS_90D, 0), 4) AS QUALITY_DISPUTE_RATE,
    ROUND(oc.REJECTED_ORDERS_90D / NULLIF(oc.TOTAL_ORDERS_90D, 0), 4) AS MERCHANT_REJECTION_RATE,
    ZEROIFNULL(dc.TOTAL_CHARGEBACK_USD) AS CHARGEBACK_DEDUCTIONS_USD,
    IFF(
        ZEROIFNULL(g.TRAILING_90D_GMV_USD) > 25000
        AND p.AVG_PREP_MIN_90D < 14.0
        AND (ZEROIFNULL(dc.QUALITY_DISPUTE_ORDERS_CNT) / NULLIF(oc.DELIVERED_ORDERS_90D, 0)) < 0.02
        AND (oc.REJECTED_ORDERS_90D / NULLIF(oc.TOTAL_ORDERS_90D, 0)) < 0.01,
        TRUE,
        FALSE
    ) AS IS_PRIME_PARTNER
FROM OPS_RAW.MRC_PARTNER_MSTR m
JOIN OPS_RAW.GEO_ZONE_LKP z ON m.ZONE_ID = z.ZONE_ID
LEFT JOIN order_counts_90d oc ON m.MRC_ID = oc.MRC_ID
LEFT JOIN gmv_90d g ON m.MRC_ID = g.MRC_ID
LEFT JOIN prep_90d p ON m.MRC_ID = p.MRC_ID
LEFT JOIN disputes_and_cbk_90d dc ON m.MRC_ID = dc.MRC_ID
WHERE m.ACTIVE_FLG = 1;

-- -----------------------------------------------------------------------------
-- Stored Procedure (Snowflake Scripting): SP_AUDIT_DISPUTE_CHARGEBACKS
-- Encodes status code definitions:
--   * RFND_STS_FLG: 0 = Pending Review, 1 = Approved Refund, 9 = Rejected Suspected Abuse
--   * PYT_STS_FLG:  0 = Scheduled Payout, 1 = Paid/Settled, 9 = Held for Compliance Review
-- -----------------------------------------------------------------------------
CREATE OR REPLACE PROCEDURE MART.SP_AUDIT_DISPUTE_CHARGEBACKS(P_HOLD_THRESHOLD_USD FLOAT)
RETURNS VARCHAR
LANGUAGE SQL
EXECUTE AS CALLER
AS
$$
DECLARE
    v_held_merchants_cnt INTEGER DEFAULT 0;
BEGIN
    UPDATE OPS_RAW.MRC_PAYOUT_LEDGER tgt
    SET PYT_STS_FLG = 9
    WHERE tgt.PYT_STS_FLG = 0
      AND tgt.REF_DOC_TXT LIKE 'STL-%'
      AND tgt.MRC_ID IN (
          SELECT MRC_ID
          FROM OPS_RAW.MRC_PAYOUT_LEDGER
          WHERE REF_DOC_TXT LIKE 'CBK-%'
          GROUP BY MRC_ID
          HAVING SUM(ABS(LEDGER_AMT_USD)) >= :P_HOLD_THRESHOLD_USD
      );

    v_held_merchants_cnt := SQLROWCOUNT;
    RETURN 'Completed settlement audit: placed ' || v_held_merchants_cnt::VARCHAR || ' scheduled merchant payouts on hold (PYT_STS_FLG=9).';
EXCEPTION
    WHEN OTHER THEN
        RETURN 'Error in SP_AUDIT_DISPUTE_CHARGEBACKS: ' || SQLERRM;
END;
$$;
