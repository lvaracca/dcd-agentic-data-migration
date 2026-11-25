---
okf_version: "0.2"
kind: AgentRouter
title: UrbanFork Marketplace Lakehouse Context Set
project: dcd-migration-demo
region: us-central1
---

# UrbanFork Data Agent Knowledge Router

This Open Knowledge Format (OKF v0.2) context bundle codifies institutional UrbanFork business rules reverse-engineered from legacy Snowflake SQL Tasks/Views/Procs, Snowpark Python, Cortex Analyst YAML, and Tableau (`.twb`) Calculated Fields.

## Routing Rules
- For **profitability, GMV, take-rate, merchant commissions, or refunds**: read [documents/concepts/platform-net-revenue.md](documents/concepts/platform-net-revenue.md) and query `urbanfork_gold_mart.FCT_PLATFORM_NET_REVENUE`.
- For **Prime Partner eligibility or kitchen prep SLAs**: read [documents/concepts/prime-partner-tier.md](documents/concepts/prime-partner-tier.md) and query `urbanfork_gold_mart.DIM_PRIME_PARTNER_SCORECARD`.
- For **live courier dispatch, idle riders, or supply deficits**: read [documents/concepts/supply-deficit-and-snapshot-trap.md](documents/concepts/supply-deficit-and-snapshot-trap.md) and query `urbanfork_gold_mart.DT_LIVE_ZONE_SUPPLY_DEFICIT` (NEVER sum `ZNE_FLEET_SNAP` across timestamps).
- For **fraud scoring or serial refund abuse**: read [documents/concepts/refund-fraud-scoring.md](documents/concepts/refund-fraud-scoring.md).
- For **table schemas, decoded status codes, and join caveats**: inspect [assets.md](assets.md).
