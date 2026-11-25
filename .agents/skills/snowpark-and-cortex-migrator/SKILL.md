---
name: snowpark-and-cortex-migrator
description: >-
  Translates the UrbanFork Snowpark Python fraud-scoring script to Google Cloud
  Managed Spark (Dataproc Serverless PySpark with spark-bigquery) and migrates
  Snowflake Cortex LLM & ML Forecast SQL to zero-shot BigQuery AI functions
  (AI.CLASSIFY, AI.SCORE, AI.FORECAST with TimesFM). Use during Act 3B.
---

# Snowpark Python & Snowflake Cortex -> Managed Spark & BigQuery AI (Act 3B)

Read `@skill:gcp-spark` and `@skill:bigquery-ai-ml` rules alongside this skill.

## Part 1: Snowpark Python -> Google Cloud Managed Spark (`gcp-target/spark/`)
Read `snowflake-source/snowpark/snowpark_merchant_fraud_scoring.py` and generate `gcp-target/spark/pyspark_fraud_scoring_serverless.py`:
1. Replace `snowflake.snowpark.Session` with PySpark / `ManagedSparkSession` (compatible with both interactive Spark Connect and `gcloud dataproc batches submit pyspark`).
2. Read `DLV_ORD_HDR`, `DSP_REFUND_FCT`, and `CUST_USER_MSTR` directly from BigQuery (`urbanfork_raw_ops`) via `spark.read.format("bigquery")`.
3. Replace the row-by-row Snowpark `@udf` (`compute_abuse_index`) with native vectorized PySpark column expressions (`F.least`, `F.when`, `F.round`) or a vectorized `@pandas_udf` for 10x faster execution!
4. Write output directly to `urbanfork_gold_mart.USER_FRAUD_RISK_SCORES` via `.write.format("bigquery").option("writeMethod", "direct").mode("overwrite")`.

## Part 2: Snowflake Cortex & ML -> Zero-Shot BigQuery AI (`gcp-target/bigquery-ai/`)
Read `snowflake-source/05_cortex_ai_and_ml.sql` and create `gcp-target/bigquery-ai/cortex_to_bq_ai.sql`:
1. **`CORTEX.CLASSIFY_TEXT` & `CORTEX.SENTIMENT` -> `AI.CLASSIFY` & `AI.SCORE`** (no `CREATE MODEL` required!):
   - Create `urbanfork_gold_mart.BQ_AI_DISPUTE_TRIAGE` over the 200 most recent rows of `DSP_REFUND_FCT` using `AI.CLASSIFY` (categories: `['Missing Item', 'Cold or Spilled Food', 'Late Courier', 'Suspected Refund Abuse']`) and `AI.SCORE` (scoring complaint urgency from 0.0 to 1.0).
2. **`SNOWFLAKE.ML.FORECAST` -> Zero-Shot `AI.FORECAST` (TimesFM)**:
   - Replace the multi-step Snowflake `CREATE SNOWFLAKE.ML.FORECAST` + `CALL ...!FORECAST` + `RESULT_SCAN` pipeline with a single zero-shot `AI.FORECAST` Table-Valued Function query predicting 14 days (`horizon => 14`) of `DAILY_ORDERS_CNT` grouped by `id_cols => ['REG_CD']`, saving to `urbanfork_gold_mart.FCT_REGIONAL_ORDER_FORECAST_14D`.
3. Validate SQL syntax with `bq query --dry_run --use_legacy_sql=false --label=datacloud:antigravity` before executing.
