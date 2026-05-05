# Databricks notebook source
# MAGIC %md
# MAGIC # 99 — Radar Simulator (DEMO AID — not production)
# MAGIC
# MAGIC ## Why this notebook exists
# MAGIC
# MAGIC In production the pricing step is **WTW Radar** — Radar reads
# MAGIC `silver.priced_book_input`, applies the rated technical price, and
# MAGIC deposits the result back as `silver.priced_book_output`.
# MAGIC
# MAGIC This notebook stands in for Radar **for self-contained demo purposes
# MAGIC only**. It applies a deliberately simple pricing formula so the
# MAGIC downstream Stage 4 aggregations and dashboard have something to
# MAGIC display without needing a real Radar connection.
# MAGIC
# MAGIC ## In production
# MAGIC
# MAGIC Replace the pricing-formula cell below with the actual Radar
# MAGIC integration — typically a file-watch or a SOAP/REST call to the
# MAGIC Radar engine, with the priced rows landed back via JDBC or CSV import.
# MAGIC The output schema (the columns this notebook writes) is the
# MAGIC contract — keep it stable. See SCHEMA_HANDOFF.md.
# MAGIC
# MAGIC ## What this simulates
# MAGIC
# MAGIC `premium = sum_insured × base_rate × flood_loading × property_adj × occupancy_adj × age_adj`
# MAGIC `expected_loss = sum_insured × flood_factor × loss_propensity × property_severity`
# MAGIC `technical_premium = expected_loss × (1 + expense_loading)`
# MAGIC `loss_ratio_estimate = expected_loss / premium`

# COMMAND ----------

dbutils.widgets.text("catalog_name",  "radar_databricks_demo")
dbutils.widgets.text("silver_schema", "silver")

catalog = dbutils.widgets.get("catalog_name")
silver  = dbutils.widgets.get("silver_schema")

input_table  = f"{catalog}.{silver}.priced_book_input"
output_table = f"{catalog}.{silver}.priced_book_output"
log_table    = f"{catalog}.{silver}.radar_run_log"

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1 — Read the priced-book input ("file received from Databricks")

# COMMAND ----------

import uuid
from datetime import datetime, timezone

run_id  = str(uuid.uuid4())[:8]
started = datetime.now(timezone.utc)

print("=" * 60)
print("  RADAR PRICING ENGINE (simulator) — run", run_id)
print("=" * 60)

input_df = spark.table(input_table)
n_in = input_df.count()
print(f"  Input rows: {n_in:,} from {input_table}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2 — Apply pricing logic
# MAGIC In production this is the Radar rated technical price. Here it is
# MAGIC a deliberately simple deterministic formula.

# COMMAND ----------

import pyspark.sql.functions as F

BASE_RATE         = 0.0025   # 25 bp on sum insured
EXPENSE_LOADING   = 0.30     # 30% expenses + capital loading on technical premium

priced = (input_df
    # Flood loading: 1.0 at flood_factor=1, 1.8 at flood_factor=2.5
    .withColumn("flood_loading", 1.0 + (F.col("flood_factor") - 1.0) * 0.8)

    # Property-type adjustment
    .withColumn("property_adj", F.expr("""
        CASE property_type
            WHEN 'Detached'      THEN 1.10
            WHEN 'Semi-Detached' THEN 1.00
            WHEN 'Terraced'      THEN 0.95
            WHEN 'Flat'          THEN 0.90
            WHEN 'Bungalow'      THEN 1.05
            ELSE                       1.00
        END
    """))

    # Occupancy adjustment
    .withColumn("occupancy_adj", F.expr("""
        CASE occupancy_type
            WHEN 'Owner-Occupied' THEN 1.00
            WHEN 'Tenanted'       THEN 1.08
            WHEN 'Holiday Let'    THEN 1.20
            WHEN 'Vacant'         THEN 1.35
            ELSE                       1.00
        END
    """))

    # Age adjustment
    .withColumn("age_adj", F.expr("""
        CASE property_age_band
            WHEN 'Pre-1900'  THEN 1.15
            WHEN '1900-1949' THEN 1.08
            WHEN '1950-1979' THEN 1.02
            WHEN '1980-1999' THEN 1.00
            WHEN '2000+'     THEN 0.95
            ELSE                  1.00
        END
    """))

    # Property severity (claim severity proxy)
    .withColumn("property_severity", F.expr("""
        CASE property_type
            WHEN 'Detached'      THEN 1.20
            WHEN 'Semi-Detached' THEN 1.00
            WHEN 'Terraced'      THEN 0.85
            WHEN 'Flat'          THEN 0.70
            WHEN 'Bungalow'      THEN 1.05
            ELSE                       1.00
        END
    """))

    # Premium: charged price
    .withColumn("premium",
        F.round(F.col("sum_insured") * F.lit(BASE_RATE)
                * F.col("flood_loading")
                * F.col("property_adj")
                * F.col("occupancy_adj")
                * F.col("age_adj"), 2))

    # Expected loss: pure burning cost view (does not include loadings)
    .withColumn("expected_loss",
        F.round(F.col("sum_insured") * F.col("flood_factor") * F.lit(0.00075)
                * F.col("property_severity"), 2))

    # Technical premium: expected loss + expense + capital loading
    .withColumn("technical_premium",
        F.round(F.col("expected_loss") * F.lit(1.0 + EXPENSE_LOADING), 2))

    # Loss-ratio estimate: expected_loss / premium
    .withColumn("loss_ratio_estimate",
        F.round(F.col("expected_loss") / F.col("premium"), 4))

    # Drop the intermediate adj cols to keep the output clean
    .drop("flood_loading", "property_adj", "occupancy_adj",
          "age_adj", "property_severity")

    .withColumn("_priced_at", F.current_timestamp())
    .withColumn("_priced_by", F.lit(f"radar_simulator:{run_id}"))
)

print(f"  Pricing applied to {n_in:,} rows")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3 — Write `silver.priced_book_output` ("file received back from Radar")

# COMMAND ----------

(priced.write
    .mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable(output_table))

spark.sql(f"""
    COMMENT ON TABLE {output_table} IS
    'Output produced by the external pricing system — WTW Radar in
     production, simulator notebook (99_radar_simulator) in this demo.
     Adds premium, technical_premium, expected_loss, and loss_ratio_estimate
     to every row from silver.priced_book_input. THIS IS THE TABLE STAGE 4
     READS to build gold.flood_concentration and gold.scenario_results.'
""")

n_out = spark.table(output_table).count()
print(f"  ✓ {output_table} — {n_out:,} rows written")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4 — Log the simulator run for audit

# COMMAND ----------

from pyspark.sql.types import (StructType, StructField, StringType,
                               IntegerType, DoubleType, TimestampType)

# Quick portfolio-level KPIs to log
kpis = priced.agg(
    F.sum("premium").alias("total_premium"),
    F.sum("expected_loss").alias("total_expected_loss"),
    F.sum("sum_insured").alias("total_exposure"),
    F.avg("loss_ratio_estimate").alias("mean_loss_ratio"),
).first()

completed = datetime.now(timezone.utc)

log_row = [{
    "run_id":              run_id,
    "input_table":         input_table,
    "output_table":        output_table,
    "rows_priced":         n_out,
    "total_premium":       float(kpis["total_premium"] or 0),
    "total_expected_loss": float(kpis["total_expected_loss"] or 0),
    "total_exposure":      float(kpis["total_exposure"] or 0),
    "mean_loss_ratio":     float(kpis["mean_loss_ratio"] or 0),
    "model_name":          "radar_simulator",
    "model_version":       "0.1.0",
    "started_at":          started,
    "completed_at":        completed,
    "status":              "SUCCESS",
}]
log_schema = StructType([
    StructField("run_id",              StringType()),
    StructField("input_table",         StringType()),
    StructField("output_table",        StringType()),
    StructField("rows_priced",         IntegerType()),
    StructField("total_premium",       DoubleType()),
    StructField("total_expected_loss", DoubleType()),
    StructField("total_exposure",      DoubleType()),
    StructField("mean_loss_ratio",     DoubleType()),
    StructField("model_name",          StringType()),
    StructField("model_version",       StringType()),
    StructField("started_at",          TimestampType()),
    StructField("completed_at",        TimestampType()),
    StructField("status",              StringType()),
])

(spark.createDataFrame(log_row, log_schema)
    .write.mode("append").saveAsTable(log_table))

spark.sql(f"""
    COMMENT ON TABLE {log_table} IS
    'Audit trail for Radar simulator runs — one row per run with KPIs, row
     counts, and timestamps. In production this is replaced by the Radar
     job log; the schema is preserved so dashboards and Genie keep working.'
""")

print()
print("=" * 60)
print("  RADAR RUN COMPLETE")
print("=" * 60)
print(f"  Run ID:              {run_id}")
print(f"  Rows priced:         {n_out:,}")
print(f"  Total premium:       £{kpis['total_premium']/1e6:,.1f}m")
print(f"  Total expected loss: £{kpis['total_expected_loss']/1e6:,.1f}m")
print(f"  Mean loss ratio:     {kpis['mean_loss_ratio']*100:.1f}%")
print("=" * 60)
