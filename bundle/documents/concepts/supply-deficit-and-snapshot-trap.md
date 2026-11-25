---
okf_version: "0.2"
kind: Concept
id: supply-deficit-and-snapshot-trap
title: Live Fleet Supply Deficit & Snapshot Trap Prevention
sources:
  - snowflake-source/03_streams_tasks_dynamic_tables.sql
  - bi-powerbi/UrbanFork_Executive_Cockpit.SemanticModel/definition/tables/DT_LIVE_ZONE_SUPPLY_DEFICIT.tmdl
---

# Live Fleet Supply Deficit Ratio (Snapshot Trap Guardrail)

- **Formula**: `UNASSIGNED_ORD_N / NULLIF(GREATEST(ONLINE_CRR_N - BUSY_CRR_N, 0), 0)`
- **Critical Deficit Zone Threshold**: `SUPPLY_DEFICIT_RATIO >= 2.50` (triggers surge dispatch alert).
- **Snapshot Trap Rule**: `ZNE_FLEET_SNAP` records 15-minute stock snapshots. NEVER sum `ONLINE_CRR_N` or `BUSY_CRR_N` across timestamps (summing London `ZNE-LON-01` produces `76,734` couriers instead of the true latest count of `95`). Always query `urbanfork_gold_mart.DT_LIVE_ZONE_SUPPLY_DEFICIT`.
