# Databricks notebook source
# MAGIC %md
# MAGIC # Stage 1 — bronze.flood_overlay
# MAGIC
# MAGIC Synthesises a UK postcode-district flood overlay table. One row per
# MAGIC postcode district. Flood scores are geographically coherent — Thames
# MAGIC Valley, Severn, Trent, Yorkshire (Calder/Aire), East Anglian fens, and
# MAGIC the south coast surge zones all carry elevated risk.
# MAGIC
# MAGIC No real Environment Agency / ABI data is used. All values are demo-grade
# MAGIC synthetic.

# COMMAND ----------

dbutils.widgets.text("catalog_name",  "radar_databricks_demo")
dbutils.widgets.text("bronze_schema", "bronze")
dbutils.widgets.text("seed",          "42")

catalog = dbutils.widgets.get("catalog_name")
schema  = dbutils.widgets.get("bronze_schema")
SEED    = int(dbutils.widgets.get("seed"))

fqn = f"{catalog}.{schema}.flood_overlay"

# COMMAND ----------

import sys, os
nb_dir = os.path.dirname(os.path.abspath(globals().get("__file__", ".")))
sys.path.insert(0, os.path.join(nb_dir, "..", "utils"))

from postcode_reference import POSTCODE_DISTRICTS  # noqa: E402

# COMMAND ----------

import random
import pandas as pd

random.seed(SEED)


def derive_flood_zone(score: int) -> str:
    """UK Environment Agency-style flood zone, derived from the demo flood_score.

    Real EA zoning is geometry-based; this approximation maps the synthetic
    score band to the four zone labels actuaries recognise.
    """
    if score >= 75:
        return "3b"   # Functional floodplain
    if score >= 55:
        return "3a"   # High probability (>1% river / >0.5% sea)
    if score >= 30:
        return "2"    # Medium probability
    return "1"        # Low probability


rows = []
for district, region, lat, lng, _pop, flood_base, watercourse, dist_m in POSTCODE_DISTRICTS:
    # Stochastic noise on top of the curated base (small; preserves the
    # geographic story). +/- 6 points.
    score = int(round(max(0, min(100, flood_base + random.gauss(0, 4)))))
    zone = derive_flood_zone(score)
    rows.append((
        district, region, zone, score,
        watercourse, dist_m, lat, lng,
    ))

pdf = pd.DataFrame(rows, columns=[
    "postcode_district", "region", "flood_zone", "flood_score",
    "nearest_watercourse", "distance_to_water_m", "centroid_lat", "centroid_lng",
])

print(f"Generated {len(pdf)} flood-overlay rows")
print()
print("Score-band distribution:")
print(pdf["flood_zone"].value_counts().reindex(["1", "2", "3a", "3b"]).to_string())

# COMMAND ----------

import pyspark.sql.functions as F
from pyspark.sql.types import (StructType, StructField, StringType, IntegerType,
                               DoubleType)

schema_def = StructType([
    StructField("postcode_district",   StringType(),  False),
    StructField("region",              StringType(),  False),
    StructField("flood_zone",          StringType(),  False),
    StructField("flood_score",         IntegerType(), False),
    StructField("nearest_watercourse", StringType(),  True),
    StructField("distance_to_water_m", IntegerType(), True),
    StructField("centroid_lat",        DoubleType(),  False),
    StructField("centroid_lng",        DoubleType(),  False),
])

df = spark.createDataFrame(pdf, schema=schema_def) \
    .withColumn("_ingested_at", F.current_timestamp())

(df.write
   .mode("overwrite")
   .option("overwriteSchema", "true")
   .saveAsTable(fqn))

spark.sql(f"""
    COMMENT ON TABLE {fqn} IS
    'Synthetic UK postcode-district flood overlay — one row per district.
     Flood scores 0–100 with EA-style zone bands (1, 2, 3a, 3b). Geographic
     coherence preserved (Thames Valley, Severn, Trent, Yorkshire Calder/
     Aire, East Anglian fens, south coast surge zones all elevated).
     Joined with bronze.property_book in stage 2 to produce
     silver.priced_book_input.'
""")

print(f"✓ {fqn} — {df.count()} rows")
