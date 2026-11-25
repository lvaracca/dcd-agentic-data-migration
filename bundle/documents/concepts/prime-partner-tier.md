---
okf_version: "0.2"
kind: Concept
id: prime-partner-tier
title: Prime Partner Tiering & SLA Telemetry Guardrails
sources:
  - snowflake-source/03_streams_tasks_dynamic_tables.sql
  - snowflake-source/04_legacy_views_and_procs.sql
  - bi-powerbi/UrbanFork_Executive_Cockpit.SemanticModel/definition/tables/DIM_PRIME_PARTNER_SCORECARD.tmdl
---

# Prime Partner Eligibility Criteria (Trailing 90 Days)

An active merchant (`MRC_PARTNER_MSTR.ACTIVE_FLG = 1`) qualifies as `IS_PRIME_PARTNER = TRUE` if and only if ALL 4 conditions hold over the trailing 90 days:
1. **Completed GMV**: `TRAILING_90D_GMV_USD > $25,000`
2. **Kitchen Prep Speed**: `AVG_PREP_MIN_90D < 14.0` minutes (excluding corrupted `app_ver = '3.8.0-beta'` telemetry pings)
3. **Quality Dispute Rate**: `< 2.0%` of delivered orders with approved quality disputes (`DSP_RSN_CD IN (1, 2)` AND `RFND_STS_FLG = 1`)
4. **Merchant Rejection Rate**: `< 1.0%` of total orders rejected (`ORD_STS_CD = 'R'`)

## Chargeback Reconciliation
Merchant chargeback deductions join `MRC_PAYOUT_LEDGER` via implicit string key: `CONCAT('CBK-', ORD_ID) = REF_DOC_TXT`.
