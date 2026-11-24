---
okf_version: "0.2"
kind: Concept
id: refund-fraud-scoring
title: Serial Refund Abuser Risk Score (Managed Spark)
sources:
  - snowflake-source/snowpark/snowpark_merchant_fraud_scoring.py
  - gcp-target/spark/pyspark_fraud_scoring_serverless.py
---

# Serial Refund Abuser Risk Score (`USER_FRAUD_RISK_SCORES`)

Computed for users with `>= 5` delivered orders (`0.0` to `1.0`):
- **50% weight**: `dispute_ratio = LEAST(total_disputes / delivered_orders, 1.0)`
- **30% weight**: `abuse_share = LEAST(flagged_abuse_disputes / total_disputes, 1.0)` where `DSP_RSN_CD = 4 OR RFND_STS_FLG = 9`
- **20% weight**: `zone_factor = IF(disputed_zones >= 3, 1.0, disputed_zones / 3.0)`

## Risk Tiers
- `FRAUD_RISK_SCORE >= 0.75`: `HIGH_RISK_BLOCK_AUTO_REFUND`
- `FRAUD_RISK_SCORE >= 0.40`: `MEDIUM_WATCHLIST`
- `< 0.40`: `LOW_NORMAL`
