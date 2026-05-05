# Databricks notebook source
# MAGIC %md
# MAGIC # Stage 4 — gold.scenario_results
# MAGIC
# MAGIC Pre-computed loss under three named flood scenarios — Thames Valley
# MAGIC 1-in-100, Severn Winter Floods, East Coast Surge (plus two more for
# MAGIC depth). Each scenario flags affected postcode districts and applies
# MAGIC a severity multiplier to the per-policy expected_loss.
# MAGIC
# MAGIC The dashboard's scenario tile reads from this table.

# COMMAND ----------

dbutils.widgets.text("catalog_name",  "radar_databricks_demo")
dbutils.widgets.text("silver_schema", "silver")
dbutils.widgets.text("gold_schema",   "gold")

catalog = dbutils.widgets.get("catalog_name")
silver  = dbutils.widgets.get("silver_schema")
gold    = dbutils.widgets.get("gold_schema")

priced_table = f"{catalog}.{silver}.priced_book_output"
out_table    = f"{catalog}.{gold}.scenario_results"

# COMMAND ----------

import sys, os
nb_dir = os.path.dirname(os.path.abspath(globals().get("__file__", ".")))
sys.path.insert(0, os.path.join(nb_dir, "..", "utils"))

from postcode_reference import FLOOD_SCENARIOS  # noqa: E402

# COMMAND ----------

import pyspark.sql.functions as F
from pyspark.sql.types import (StructType, StructField, StringType,
                               IntegerType, DoubleType, ArrayType)

priced = spark.table(priced_table).select(
    "policy_id", "postcode_district", "sum_insured",
    "premium", "expected_loss",
).cache()

scenario_rows = []
detail_rows   = []   # per-(scenario, district) drill-down

for scenario_name, cfg in FLOOD_SCENARIOS.items():
    affected = cfg["districts"]
    severity = cfg["severity_multiplier"]
    narrative = cfg["narrative"]

    affected_df = priced.where(F.col("postcode_district").isin(affected))

    summary = affected_df.agg(
        F.count("*").alias("policy_count"),
        F.sum("sum_insured").alias("total_exposure"),
        F.sum("premium").alias("total_premium"),
        F.sum("expected_loss").alias("base_expected_loss"),
    ).first()

    pol_count   = int(summary["policy_count"] or 0)
    exposure    = float(summary["total_exposure"] or 0)
    premium     = float(summary["total_premium"] or 0)
    base_el     = float(summary["base_expected_loss"] or 0)
    scen_loss   = base_el * severity

    scenario_rows.append({
        "scenario":             scenario_name,
        "narrative":            narrative,
        "severity_multiplier":  severity,
        "affected_districts":   affected,
        "districts_count":      len(affected),
        "policy_count":         pol_count,
        "total_exposure":       exposure,
        "total_premium":        premium,
        "base_expected_loss":   base_el,
        "scenario_loss":        scen_loss,
        # Headline ratio: scenario loss as % of total premium for the
        # affected districts (proxy for "could one event wipe out the
        # premium we collected from this cluster?")
        "loss_to_premium_pct":  round((scen_loss / premium * 100) if premium else 0, 1),
    })

    # Per-district drill-down
    per_district = (affected_df
        .groupBy("postcode_district")
        .agg(
            F.count("*").alias("policy_count"),
            F.sum("sum_insured").alias("total_exposure"),
            F.sum("expected_loss").alias("base_expected_loss"),
        )
        .withColumn("scenario", F.lit(scenario_name))
        .withColumn("severity_multiplier", F.lit(severity))
        .withColumn("scenario_loss",
                    F.col("base_expected_loss") * F.lit(severity))
        .select("scenario", "postcode_district", "severity_multiplier",
                "policy_count", "total_exposure",
                "base_expected_loss", "scenario_loss")
    )
    detail_rows.append(per_district)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Write `gold.scenario_results` (one row per scenario)

# COMMAND ----------

scen_schema = StructType([
    StructField("scenario",            StringType()),
    StructField("narrative",           StringType()),
    StructField("severity_multiplier", DoubleType()),
    StructField("affected_districts",  ArrayType(StringType())),
    StructField("districts_count",     IntegerType()),
    StructField("policy_count",        IntegerType()),
    StructField("total_exposure",      DoubleType()),
    StructField("total_premium",       DoubleType()),
    StructField("base_expected_loss",  DoubleType()),
    StructField("scenario_loss",       DoubleType()),
    StructField("loss_to_premium_pct", DoubleType()),
])

(spark.createDataFrame(scenario_rows, scen_schema)
    .withColumn("_built_at", F.current_timestamp())
    .write.mode("overwrite").option("overwriteSchema", "true")
    .saveAsTable(out_table))

spark.sql(f"""
    COMMENT ON TABLE {out_table} IS
    'Pre-computed loss under named flood scenarios. One row per scenario
     (Thames Valley 1-in-100, Severn Winter Floods, East Coast Surge,
     Yorkshire Calder/Aire, South Coast Storm). Each row applies a severity
     multiplier to the sum of expected_loss across the scenario''s affected
     postcode districts. Drives the dashboard scenario stress tile.'
""")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Write `gold.scenario_district_detail` (per-(scenario, district))

# COMMAND ----------

from functools import reduce
from pyspark.sql import DataFrame

detail_df = reduce(DataFrame.unionByName, detail_rows)
detail_table = f"{catalog}.{gold}.scenario_district_detail"

(detail_df.write.mode("overwrite").option("overwriteSchema", "true")
    .saveAsTable(detail_table))

spark.sql(f"""
    COMMENT ON TABLE {detail_table} IS
    'Per-(scenario, district) drill-down for gold.scenario_results. One row
     per affected district per scenario, with policy count, exposure, base
     expected loss, and scenario_loss = base × severity. Used by the
     dashboard scenario drill-down view.'
""")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

print(f"\nWrote {out_table} ({len(scenario_rows)} scenarios) and {detail_table}")
spark.table(out_table).select(
    "scenario", "districts_count", "policy_count",
    F.round(F.col("total_exposure") / 1e6, 0).alias("exposure_m"),
    F.round(F.col("total_premium")  / 1e6, 2).alias("premium_m"),
    F.round(F.col("scenario_loss")  / 1e6, 2).alias("scenario_loss_m"),
    "loss_to_premium_pct",
).orderBy(F.col("scenario_loss").desc()).show(truncate=False)
