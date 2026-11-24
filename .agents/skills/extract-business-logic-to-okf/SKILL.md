---
name: extract-business-logic-to-okf
description: >-
  Reverse-engineers undocumented QuickBite business rules, status flags, KPI
  formulas, and join traps out of Snowflake SQL Views/Tasks/Procs, Snowpark
  Python, legacy cortex_ops_model.yaml, and Power BI (.tmdl) DAX measures into
  an Open Knowledge Format (OKF v0.2) repository, enriches BigQuery metadata,
  seeds QUERY_HISTORY for Usage-Based Data Insights, and prepares Knowledge
  Catalog Business Glossary & Context Set publishing. Use during Act 4.
---

# Business Logic Reverse-Engineering -> OKF v0.2 & Knowledge Catalog (Act 4)

> **Important**: When asked to publish a remote Knowledge Catalog Context Set via `kcmd`, load and obey `@skill:curate-context` (including its Gate 1 / Gate 2 approval workflow and grounding rules).

## Sources of Institutional Knowledge to Harvest
Inspect all 4 codebase pillars (never guess meanings from column names alone—cite exact source files!):
1. **Snowflake Orchestrator & Views**: `snowflake-source/03_streams_tasks_dynamic_tables.sql` & `snowflake-source/04_legacy_views_and_procs.sql`
   - Decodes `VERT_CD` (`1`=Restaurant, `2`=Grocery), `ORD_STS_CD` (`'D'`, `'P'`, `'C'`, `'R'`), `DSP_RSN_CD` (`1`=Missing Item, `2`=Cold/Spilled, `3`=Extreme Late SLA, `4`=Suspected Abuse), `RFND_STS_FLG` (`0`/`1`/`9`), `PYT_STS_FLG` (`0`/`1`/`9`).
   - Captures the **4 Analytical Traps**: SCD2 Commission dates (`CAL_DT BETWEEN EFF_FROM_DT AND EFF_TO_DT`), Anti-Fanout Refund CTE, Live Fleet Snapshot (`MAX(SNAP_TS)`), and Chargeback String Concat (`CONCAT('CBK-', ORD_ID) = REF_DOC_TXT`), plus excluding `app_ver = '3.8.0-beta'` on JSON pings!
2. **Snowpark Python**: `snowflake-source/snowpark/snowpark_merchant_fraud_scoring.py`
   - Extracts `Serial Refund Abuser Score` (`0.50*dispute_ratio + 0.30*abuse_share + 0.20*zone_factor` for `>= 5` delivered orders) and `High Fraud Risk User` (`>= 0.75`).
3. **Legacy Cortex YAML**: `snowflake-source/cortex-analyst/cortex_ops_model.yaml`
   - Preserves synonyms and the critical rule: *Courier Tips (`TIP_USD`) are 100% pass-through and must NEVER be included in Platform Net Revenue*.
4. **Power BI Semantic Model (`.tmdl` DAX)**: `bi-powerbi/QuickBite_Executive_Cockpit.SemanticModel/definition/tables/*.tmdl`
   - Harvests the 11 official executive DAX definitions (`Platform Net Revenue ($)`, `Effective Take-Rate %`, `Active Prime Partners`, `Prime GMV Share %`, `Order-Weighted Kitchen Prep (Min)`, `Live Supply Deficit Ratio`, `Critical Deficit Zones >= 2.50`).

## Output Artifacts to Generate

1. **OKF v0.2 Context Set Bundle (`bundle/`)**:
   - `bundle/agents.md` (Root router for data agents)
   - `bundle/assets.md` & `bundle/assets/bigquery/<project>/quickbite_raw_ops/<table>.md` + `quickbite_gold_mart/<table>.md` (`Table Context` pages with grain, decoded column descriptions, join caveats, and compile-checked `GOOGLE_SQL` golden queries in `dataplex-types.global.queries`)
   - `bundle/documents.md` & `bundle/documents/concepts/*.md` (`Concept` pages for `platform-net-revenue.md`, `prime-partner-tier.md`, `supply-deficit-and-snapshot-trap.md`, `sla-breach-and-telemetry-caveats.md`, `refund-fraud-scoring.md`)
   - `bundle/_links.yaml`
2. **Structured Metadata & Conversational Analytics Config (`okf/`)**:
   - `okf/bigquery_metadata_manifest.json` (dataset, table, and column descriptions mapped from `bundle/` for automated BigQuery schema enrichment; see format required by [push_okf_metadata_and_seed_history.py](./scripts/push_okf_metadata_and_seed_history.py))
   - `okf/conversational-analytics/agent_system_prompt.md` (Clarification Triggers for Vertical `Restaurant vs Grocery` and Revenue `GMV vs Platform Net Revenue`, fiscal calendar starting Feb 1, no raw SQL in prompt)
   - `okf/conversational-analytics/agent_golden_queries.md` (8 verified GoogleSQL queries)

## Forward-Engineering to BigQuery & Seeding Usage-Based Joins
Run [push_okf_metadata_and_seed_history.py](./scripts/push_okf_metadata_and_seed_history.py) via `.venv/bin/python`:
```bash
.venv/bin/python .agents/skills/extract-business-logic-to-okf/scripts/push_okf_metadata_and_seed_history.py
```
This script pushes all extracted table & column descriptions to BigQuery AND executes the translated Snowflake `QUERY_HISTORY` join queries against BigQuery so **Knowledge Catalog Data Insights** builds deterministic **Usage-based Joins**!
