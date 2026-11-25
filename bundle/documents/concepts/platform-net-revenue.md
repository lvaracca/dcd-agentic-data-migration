---
okf_version: "0.2"
kind: Concept
id: platform-net-revenue
title: Platform Net Revenue (Net Take) & Effective Take-Rate
sources:
  - snowflake-source/03_streams_tasks_dynamic_tables.sql
  - snowflake-source/04_legacy_views_and_procs.sql
  - bi-powerbi/UrbanFork_Executive_Cockpit.SemanticModel/definition/tables/FCT_PLATFORM_NET_REVENUE.tmdl
---

# Platform Net Revenue (Net Take)

## Official Definition
UrbanFork's core profitability metric computed over **completed delivered orders (`ORD_STS_CD = 'D'`)**:

$$\text{Platform Net Revenue} = \text{Merchant SCD2 Commission} + \text{Delivery Fees} + \text{Service Fees} - \text{Courier Pay} - \text{Promo Subsidies} - \text{Approved Refunds}$$

- **Courier Tips (`TIP_USD`)**: 100% pass-through to couriers — NEVER included in Platform Net Revenue.
- **Effective Take-Rate %**: `DIVIDE([Platform Net Revenue ($)], [Total GMV ($)], 0)` (Power BI DAX).

## Analytical Guardrails
1. **SCD Type 2 Commission Trap**: Always join `MRC_COMM_SCD2` on `CAL_DT BETWEEN EFF_FROM_DT AND EFF_TO_DT`. Using `IS_CURR_FLG = 1` overstates Q3 2025 Restaurant Net Revenue by `+$127,296.80` (`$280,447.29` vs `$153,150.49`).
2. **Refund Fan-Out Trap**: Pre-aggregate `DSP_REFUND_FCT` (`WHERE RFND_STS_FLG = 1`) at `ORD_ID` grain before joining item lines (`$248,632.85` true vs `$813,512.14` fanned-out).
3. **Fiscal Calendar**: UrbanFork's fiscal year starts on **February 1st** (`SYS_CAL_DIM.FISC_YR_N`).
