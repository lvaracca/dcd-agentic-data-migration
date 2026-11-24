# QuickBite Certified Golden Queries (GoogleSQL)

## 1. Q3 2025 Calendar Restaurant Platform Net Revenue (SCD2 Verified = $153,150.49)
```sql
SELECT
  VERTICAL_NM,
  SUM(COMPLETED_ORDERS_CNT) AS orders_cnt,
  ROUND(SUM(GROSS_MERCHANDISE_VALUE_USD), 2) AS gmv_usd,
  ROUND(SUM(PLATFORM_NET_REVENUE_USD), 2) AS platform_net_revenue_usd,
  ROUND(SAFE_DIVIDE(SUM(PLATFORM_NET_REVENUE_USD), SUM(GROSS_MERCHANDISE_VALUE_USD)), 4) AS effective_take_rate
FROM `dcd-migration-demo.quickbite_gold_mart.FCT_PLATFORM_NET_REVENUE`
WHERE CAL_DT BETWEEN '2025-07-01' AND '2025-09-30'
  AND VERT_CD = 1
GROUP BY 1;
```

## 2. FY 2025 Fiscal Net Revenue by Vertical (Fiscal Year Starts Feb 1)
```sql
SELECT
  FISC_YR_N,
  VERTICAL_NM,
  ROUND(SUM(PLATFORM_NET_REVENUE_USD), 2) AS platform_net_revenue_usd,
  ROUND(SUM(APPROVED_REFUNDS_USD), 2) AS approved_refunds_usd
FROM `dcd-migration-demo.quickbite_gold_mart.FCT_PLATFORM_NET_REVENUE`
WHERE FISC_YR_N = 2025
GROUP BY 1, 2
ORDER BY 2 DESC;
```

## 3. Top 3 Critical Live Fleet Supply Deficit Zones (Snapshot-Trap Safe)
```sql
SELECT
  ZONE_ID,
  CITY_NM,
  REG_CD,
  ONLINE_CRR_N,
  BUSY_CRR_N,
  IDLE_CRR_N,
  UNASSIGNED_ORD_N,
  SUPPLY_DEFICIT_RATIO
FROM `dcd-migration-demo.quickbite_gold_mart.DT_LIVE_ZONE_SUPPLY_DEFICIT`
ORDER BY SUPPLY_DEFICIT_RATIO DESC
LIMIT 5;
```

## 4. Active EMEA Prime Partners & Order-Weighted Kitchen Prep Time
```sql
SELECT
  REG_CD,
  COUNTIF(IS_PRIME_PARTNER) AS active_prime_partners,
  ROUND(
    SAFE_DIVIDE(
      SUM(IF(IS_PRIME_PARTNER, TRAILING_90D_GMV_USD, 0)),
      SUM(TRAILING_90D_GMV_USD)
    ) * 100, 2
  ) AS prime_gmv_share_pct,
  ROUND(
    SAFE_DIVIDE(
      SUM(AVG_PREP_MIN_90D * DELIVERED_ORDERS_90D),
      SUM(DELIVERED_ORDERS_90D)
    ), 2
  ) AS order_weighted_prep_min
FROM `dcd-migration-demo.quickbite_gold_mart.DIM_PRIME_PARTNER_SCORECARD`
WHERE REG_CD = 'EMEA'
GROUP BY 1;
```

## 5. Anti-Fanout Approved Refunds Verification ($248,632.85)
```sql
SELECT
  ROUND(SUM(APPROVED_REFUNDS_USD), 2) AS total_approved_refunds_usd
FROM `dcd-migration-demo.quickbite_gold_mart.FCT_PLATFORM_NET_REVENUE`
WHERE CAL_DT <= '2026-03-31';
```

## 6. Merchant Chargeback Recovery Reconciliation ('CBK-' || ORD_ID)
```sql
SELECT
  m.MRC_ID,
  m.MRC_NM,
  COUNT(DISTINCT d.ORD_ID) AS charged_back_orders,
  ROUND(SUM(ABS(led.LEDGER_AMT_USD)), 2) AS total_chargebacks_usd
FROM `dcd-migration-demo.quickbite_raw_ops.DSP_REFUND_FCT` d
JOIN `dcd-migration-demo.quickbite_raw_ops.DLV_ORD_HDR` h ON d.ORD_ID = h.ORD_ID
JOIN `dcd-migration-demo.quickbite_raw_ops.MRC_PARTNER_MSTR` m ON h.MRC_ID = m.MRC_ID
JOIN `dcd-migration-demo.quickbite_raw_ops.MRC_PAYOUT_LEDGER` led
  ON CONCAT('CBK-', d.ORD_ID) = led.REF_DOC_TXT
GROUP BY 1, 2
ORDER BY 4 DESC
LIMIT 10;
```

## 7. Next 14-Day Regional Order Forecast (Zero-Shot TimesFM 2.5)
```sql
SELECT
  REG_CD,
  DATE(FORECAST_DAY_TS) AS forecast_dt,
  FORECAST_ORDERS_CNT,
  LOWER_BOUND_95,
  UPPER_BOUND_95
FROM `dcd-migration-demo.quickbite_gold_mart.FCT_REGIONAL_ORDER_FORECAST_14D`
ORDER BY REG_CD, forecast_dt;
```

## 8. BigQuery AI Dispute Triage Summary (AI.CLASSIFY + AI.SCORE)
```sql
SELECT
  BQ_AI_PREDICTED_CATEGORY,
  COUNT(*) AS ticket_cnt,
  ROUND(AVG(BQ_AI_URGENCY_SCORE), 3) AS avg_urgency_score,
  ROUND(SUM(RFND_AMT_USD), 2) AS total_refund_requested_usd
FROM `dcd-migration-demo.quickbite_gold_mart.BQ_AI_DISPUTE_TRIAGE`
GROUP BY 1
ORDER BY avg_urgency_score DESC;
```
