"""
QuickBite Legacy Snowpark Python Workload: User Refund-Abuse & Fraud Risk Scoring
---------------------------------------------------------------------------------
Migrated by Antigravity during Act 3 to:
  -> Google Cloud Managed Spark (Dataproc Serverless) via ManagedSparkSession
     and the direct BigQuery Storage Read/Write connector (spark-bigquery),
     converting the row-by-row Python @udf into a vectorized PySpark UDF.

Business Logic Embedded in Code (Extracted by Antigravity to OKF & Knowledge Catalog):
  * Serial Refund Abuser Score (0.0 to 1.0):
      Weighted composite over a user's lifetime completed orders (>= 5 orders):
        - 50% weight: dispute_rate (total disputes / delivered orders, capped at 1.0)
        - 30% weight: abuse_reason_share (share of disputes flagged DSP_RSN_CD = 4
          or rejected RFND_STS_FLG = 9)
        - 20% weight: multi_zone_spread (distinct delivery zones disputed >= 3 -> 1.0)
  * High Fraud Risk User: fraud_risk_score >= 0.75 (recommended for instant-refund block)
"""

import os
from snowflake.snowpark import Session
from snowflake.snowpark import functions as F
from snowflake.snowpark.types import FloatType, IntegerType


def compute_abuse_index(
    delivered_cnt: int,
    dispute_cnt: int,
    flagged_abuse_cnt: int,
    distinct_dispute_zones: int,
) -> float:
    if not delivered_cnt or delivered_cnt < 5 or not dispute_cnt:
        return 0.0
    dispute_ratio = min(dispute_cnt / float(delivered_cnt), 1.0)
    abuse_share = min(flagged_abuse_cnt / float(dispute_cnt), 1.0)
    zone_factor = 1.0 if distinct_dispute_zones >= 3 else (distinct_dispute_zones / 3.0)
    score = (0.50 * dispute_ratio) + (0.30 * abuse_share) + (0.20 * zone_factor)
    return round(min(max(score, 0.0), 1.0), 4)


def run_snowpark_scoring(session: Session) -> None:
    abuse_udf = F.udf(
        compute_abuse_index,
        return_type=FloatType(),
        input_types=[IntegerType(), IntegerType(), IntegerType(), IntegerType()],
        name="UDF_COMPUTE_ABUSE_INDEX",
        is_permanent=False,
        replace=True,
    )

    orders_df = session.table("QUICKBITE_PROD.OPS_RAW.DLV_ORD_HDR").filter(
        F.col("ORD_STS_CD") == F.lit("D")
    )
    disputes_df = session.table("QUICKBITE_PROD.OPS_RAW.DSP_REFUND_FCT")
    users_df = session.table("QUICKBITE_PROD.OPS_RAW.CUST_USER_MSTR")

    ord_joined = orders_df.join(disputes_df, on="ORD_ID", how="left")

    user_metrics = ord_joined.group_by("USR_ID").agg(
        F.count_distinct("ORD_ID").cast(IntegerType()).alias("DELIVERED_ORDERS_CNT"),
        F.count_distinct("DSP_ID").cast(IntegerType()).alias("TOTAL_DISPUTES_CNT"),
        F.sum(
            F.iff(
                (F.col("DSP_RSN_CD") == 4) | (F.col("RFND_STS_FLG") == 9),
                1,
                0,
            )
        )
        .cast(IntegerType())
        .alias("FLAGGED_ABUSE_DISPUTES_CNT"),
        F.count_distinct(F.iff(F.col("DSP_ID").is_not_null(), F.col("ZONE_ID"), None))
        .cast(IntegerType())
        .alias("DISPUTED_ZONES_CNT"),
        F.coalesce(F.sum(F.iff(F.col("RFND_STS_FLG") == 1, F.col("RFND_AMT_USD"), 0.0)), F.lit(0.0)).alias(
            "APPROVED_REFUND_TOTAL_USD"
        ),
    )

    scored_df = (
        user_metrics.join(
            users_df.select("USR_ID", "HOME_ZONE_ID", "QB_PASS_FLG"),
            on="USR_ID",
            how="inner",
        )
        .with_column(
            "FRAUD_RISK_SCORE",
            abuse_udf(
                F.col("DELIVERED_ORDERS_CNT"),
                F.col("TOTAL_DISPUTES_CNT"),
                F.col("FLAGGED_ABUSE_DISPUTES_CNT"),
                F.col("DISPUTED_ZONES_CNT"),
            ),
        )
        .with_column(
            "RISK_TIER",
            F.iff(
                F.col("FRAUD_RISK_SCORE") >= 0.75,
                F.lit("HIGH_RISK_BLOCK_AUTO_REFUND"),
                F.iff(F.col("FRAUD_RISK_SCORE") >= 0.40, F.lit("MEDIUM_WATCHLIST"), F.lit("LOW_NORMAL")),
            ),
        )
    )

    scored_df.write.mode("overwrite").save_as_table("QUICKBITE_PROD.MART.USER_FRAUD_RISK_SCORES")


if __name__ == "__main__":
    conn_params = {
        "account": os.environ["SNOWFLAKE_ACCOUNT"],
        "user": os.environ["SNOWFLAKE_USER"],
        "password": os.environ["SNOWFLAKE_PASSWORD"],
        "role": os.environ.get("SNOWFLAKE_ROLE", "ACCOUNTADMIN"),
        "warehouse": os.environ.get("SNOWFLAKE_WAREHOUSE", "QB_TRANSFORM_WH"),
        "database": os.environ.get("SNOWFLAKE_DATABASE", "QUICKBITE_PROD"),
        "schema": "MART",
    }
    sf_session = Session.builder.configs(conn_params).create()
    try:
        run_snowpark_scoring(sf_session)
        print("Successfully materialized QUICKBITE_PROD.MART.USER_FRAUD_RISK_SCORES via Snowpark!")
    finally:
        sf_session.close()
