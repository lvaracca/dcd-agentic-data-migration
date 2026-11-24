-- =============================================================================
-- QuickBite Snowflake Source Setup — Step 7: Seed Realistic Analyst Query History
-- Executed during setup so SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY (and
-- INFORMATION_SCHEMA.QUERY_HISTORY()) captures real multi-table joins across
-- SCD2 commissions, 'CBK-' string concatenations, Snapshot MAX(SNAP_TS), and
-- VARIANT JSON pings. Antigravity translates & replays these in BigQuery to
-- power deterministic Usage-Based Joins in Knowledge Catalog Data Insights!
-- =============================================================================
USE ROLE ACCOUNTADMIN;
USE WAREHOUSE QB_TRANSFORM_WH;
USE DATABASE QUICKBITE_PROD;

-- Query 1: Calendar Q3 2025 Restaurant Platform Net Revenue (SCD2 + Anti-Fanout)
SELECT
    VERT_CD,
    VERTICAL_NM,
    ROUND(SUM(PLATFORM_NET_REVENUE_USD), 2) AS Q3_2025_NET_REV_USD
FROM MART.VW_PLATFORM_NET_REVENUE
WHERE CAL_DT BETWEEN '2025-07-01' AND '2025-09-30'
  AND VERT_CD = 1
GROUP BY 1, 2;

-- Query 2: Fiscal Year 2025 Net Revenue by Vertical & Region
SELECT
    FISC_YR_N,
    REG_CD,
    VERTICAL_NM,
    SUM(COMPLETED_ORDERS_CNT) AS ORDERS_CNT,
    ROUND(SUM(GROSS_MERCHANDISE_VALUE_USD), 2) AS GMV_USD,
    ROUND(SUM(PLATFORM_NET_REVENUE_USD), 2) AS NET_REVENUE_USD
FROM MART.VW_PLATFORM_NET_REVENUE
WHERE FISC_YR_N = 2025
GROUP BY 1, 2, 3
ORDER BY NET_REVENUE_USD DESC;

-- Query 3: Direct Multi-Table Join across Orders, SCD2 Commissions, Calendar & Zones
SELECT
    z.REG_CD,
    cal.FISC_YR_N,
    cal.FISC_QTR_N,
    ROUND(SUM(ln.QTY_N * ln.UNIT_PRC_USD * scd.COMM_RATE_PCT), 2) AS TRUE_COMMISSION_USD
FROM OPS_RAW.DLV_ORD_HDR h
JOIN OPS_RAW.DLV_ORD_ITEM_LN ln ON h.ORD_ID = ln.ORD_ID
JOIN OPS_RAW.SYS_CAL_DIM cal ON h.ORD_DT_SK = cal.DT_SK
JOIN OPS_RAW.GEO_ZONE_LKP z ON h.ZONE_ID = z.ZONE_ID
JOIN OPS_RAW.MRC_COMM_SCD2 scd
    ON h.MRC_ID = scd.MRC_ID
   AND cal.CAL_DT BETWEEN scd.EFF_FROM_DT AND scd.EFF_TO_DT
WHERE h.ORD_STS_CD = 'D'
GROUP BY 1, 2, 3;

-- Query 4: Chargeback Reconciliation using Implicit String-Prefix Join ('CBK-' || ORD_ID)
SELECT
    m.MRC_NM,
    z.CITY_NM,
    COUNT(DISTINCT d.DSP_ID) AS QUALITY_DISPUTES,
    SUM(d.RFND_AMT_USD) AS APPROVED_REFUNDS_USD,
    SUM(ABS(led.LEDGER_AMT_USD)) AS RECOVERED_CHARGEBACKS_USD
FROM OPS_RAW.DSP_REFUND_FCT d
JOIN OPS_RAW.DLV_ORD_HDR h ON d.ORD_ID = h.ORD_ID
JOIN OPS_RAW.MRC_PARTNER_MSTR m ON h.MRC_ID = m.MRC_ID
JOIN OPS_RAW.GEO_ZONE_LKP z ON m.ZONE_ID = z.ZONE_ID
JOIN OPS_RAW.MRC_PAYOUT_LEDGER led ON CONCAT('CBK-', h.ORD_ID) = led.REF_DOC_TXT
WHERE d.RFND_STS_FLG = 1
  AND d.DSP_RSN_CD IN (1, 2)
GROUP BY 1, 2
ORDER BY RECOVERED_CHARGEBACKS_USD DESC
LIMIT 20;

-- Query 5: Latest Snapshot Fleet Supply Deficit (Avoiding the Snapshot Trap!)
SELECT
    z.CITY_NM,
    z.REG_CD,
    s.SNAP_TS,
    s.ONLINE_CRR_N,
    (s.ONLINE_CRR_N - s.BUSY_CRR_N) AS IDLE_COURIERS,
    s.UNASSIGNED_ORD_N,
    ROUND(s.UNASSIGNED_ORD_N / NULLIF(s.ONLINE_CRR_N - s.BUSY_CRR_N, 0), 2) AS DEFICIT_RATIO
FROM OPS_RAW.ZNE_FLEET_SNAP s
JOIN OPS_RAW.GEO_ZONE_LKP z ON s.ZONE_ID = z.ZONE_ID
WHERE s.SNAP_TS = (SELECT MAX(SNAP_TS) FROM OPS_RAW.ZNE_FLEET_SNAP)
ORDER BY DEFICIT_RATIO DESC
LIMIT 10;

-- Query 6: QuickPass Subscriber Retention & Courier Vehicle Performance
SELECT
    u.QB_PASS_FLG,
    c.VEH_TP_CD,
    COUNT(DISTINCT h.ORD_ID) AS DELIVERED_ORDERS,
    ROUND(AVG(TRY_TO_NUMBER(p.PAYLOAD:metrics.travel_sec::VARCHAR) / 60.0), 2) AS AVG_TRAVEL_MIN
FROM OPS_RAW.DLV_ORD_HDR h
JOIN OPS_RAW.CUST_USER_MSTR u ON h.USR_ID = u.USR_ID
JOIN OPS_RAW.CRR_COURIER_MSTR c ON h.CRR_ID = c.CRR_ID
JOIN IOT_RAW.APP_DELIVERY_PINGS p ON h.ORD_ID = p.ORD_ID
WHERE h.ORD_STS_CD = 'D'
  AND p.PAYLOAD:stage::VARCHAR = 'DELIVERED'
  AND p.PAYLOAD:app_ver::VARCHAR != '3.8.0-beta'
GROUP BY 1, 2;
