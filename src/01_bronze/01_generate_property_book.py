# Databricks notebook source
# MAGIC %md
# MAGIC # Stage 1 — bronze.property_book
# MAGIC
# MAGIC Synthesises a UK home insurance portfolio of ~50,000 policies and lands
# MAGIC them as `bronze.property_book`. Geographic distribution is weighted
# MAGIC toward population centres (London, Manchester, Birmingham, Leeds,
# MAGIC Glasgow, etc.), not uniform.
# MAGIC
# MAGIC Idempotent — re-runs overwrite. Deterministic — same seed, same data.

# COMMAND ----------

dbutils.widgets.text("catalog_name",  "radar_databricks_demo")
dbutils.widgets.text("bronze_schema", "bronze")
dbutils.widgets.text("num_policies",  "50000")
dbutils.widgets.text("seed",          "42")

catalog = dbutils.widgets.get("catalog_name")
schema  = dbutils.widgets.get("bronze_schema")
N       = int(dbutils.widgets.get("num_policies"))
SEED    = int(dbutils.widgets.get("seed"))

fqn = f"{catalog}.{schema}.property_book"

# COMMAND ----------

import sys, os
# In Databricks the bundle path is /Workspace/.../src/01_bronze — utils sit
# alongside in src/utils. Add the parent so the import works in both Databricks
# and local-notebook contexts.
nb_dir = os.path.dirname(os.path.abspath(globals().get("__file__", ".")))
sys.path.insert(0, os.path.join(nb_dir, "..", "utils"))

from postcode_reference import POSTCODE_DISTRICTS  # noqa: E402

# COMMAND ----------

import random
import pandas as pd
from datetime import date, timedelta

random.seed(SEED)

# Districts + weights for population-weighted sampling
districts = [r[0] for r in POSTCODE_DISTRICTS]
pop_weights = [r[4] for r in POSTCODE_DISTRICTS]
region_lookup = {r[0]: r[1] for r in POSTCODE_DISTRICTS}

# Property-type mix varies by region: London more flats, suburban more detached.
PROPERTY_TYPE_MIX = {
    # region:                  detached, semi, terraced, flat, bungalow
    "London":                  [ 4, 12, 28, 52,  4],
    "South East":              [22, 28, 26, 18,  6],
    "South West":              [26, 26, 24, 14, 10],
    "East":                    [24, 28, 24, 16,  8],
    "Midlands":                [18, 30, 28, 18,  6],
    "North West":              [14, 28, 32, 20,  6],
    "Yorkshire":               [16, 30, 30, 18,  6],
    "North East":              [14, 30, 32, 18,  6],
    "Wales":                   [22, 28, 26, 14, 10],
    "Scotland":                [16, 22, 26, 30,  6],
    "Northern Ireland":        [22, 28, 26, 16,  8],
}
PROPERTY_TYPES = ["Detached", "Semi-Detached", "Terraced", "Flat", "Bungalow"]

# Sum-insured base by region (median; lognormal sigma applied below).
# London + SE materially higher; Northern + Welsh lower. £k.
REGION_SI_BASE = {
    "London":           520,
    "South East":       420,
    "South West":       340,
    "East":             340,
    "Midlands":         260,
    "North West":       240,
    "Yorkshire":        230,
    "North East":       210,
    "Wales":            220,
    "Scotland":         240,
    "Northern Ireland": 200,
}

# Property type adjustments (multiplicative on sum-insured)
PROPERTY_TYPE_SI_ADJ = {
    "Detached":      1.55,
    "Semi-Detached": 1.05,
    "Terraced":      0.85,
    "Flat":          0.70,
    "Bungalow":      0.95,
}

OCCUPANCY = ["Owner-Occupied", "Tenanted", "Holiday Let", "Vacant"]
OCCUPANCY_WEIGHTS = [76, 20, 3, 1]

today = date(2026, 5, 1)

print(f"Generating {N:,} policies (seed={SEED}) across {len(districts)} districts...")

# COMMAND ----------

rows = []
for i in range(N):
    pid = f"POL-{1_000_000 + i}"
    district = random.choices(districts, weights=pop_weights, k=1)[0]
    region   = region_lookup[district]

    # Property type
    ptype = random.choices(PROPERTY_TYPES, weights=PROPERTY_TYPE_MIX[region], k=1)[0]

    # Sum insured: lognormal around region base × property-type multiplier
    base = REGION_SI_BASE[region] * PROPERTY_TYPE_SI_ADJ[ptype]
    # ln-mean, ln-sigma chosen so the median sits near `base` and the spread is
    # plausible for UK home insurance.
    import math
    si_k = round(random.lognormvariate(math.log(base), 0.45))
    sum_insured = max(60, min(si_k, 5000)) * 1000  # cap 60k–5m, in £

    # Build year: heavy-tailed older for Victorian / Edwardian, modern bump
    # for new-builds. Crude weights by decade.
    decade_weights = [
        (1880, 1), (1890, 2), (1900, 4), (1910, 4), (1920, 5), (1930, 8),
        (1940, 3), (1950, 7), (1960, 9), (1970, 9), (1980, 11), (1990, 10),
        (2000, 12), (2010, 10), (2020, 5),
    ]
    decade_starts = [d[0] for d in decade_weights]
    decade_w      = [d[1] for d in decade_weights]
    dec = random.choices(decade_starts, weights=decade_w, k=1)[0]
    build_year = min(2025, dec + random.randint(0, 9))

    occ = random.choices(OCCUPANCY, weights=OCCUPANCY_WEIGHTS, k=1)[0]

    # Inception: uniform over the last 12 months
    inception = today - timedelta(days=random.randint(0, 365))

    rows.append((pid, district, sum_insured, ptype, build_year, occ, inception))

pdf = pd.DataFrame(rows, columns=[
    "policy_id", "postcode_district", "sum_insured",
    "property_type", "build_year", "occupancy_type", "inception_date",
])

print(f"Generated {len(pdf):,} policies")
print(f"Total sum insured: £{pdf['sum_insured'].sum() / 1e9:,.1f}bn")

# COMMAND ----------

import pyspark.sql.functions as F
from pyspark.sql.types import (StructType, StructField, StringType, LongType,
                               IntegerType, DateType)

schema_def = StructType([
    StructField("policy_id",          StringType(),  False),
    StructField("postcode_district",  StringType(),  False),
    StructField("sum_insured",        LongType(),    False),
    StructField("property_type",      StringType(),  False),
    StructField("build_year",         IntegerType(), False),
    StructField("occupancy_type",     StringType(),  False),
    StructField("inception_date",     DateType(),    False),
])

df = spark.createDataFrame(pdf, schema=schema_def) \
    .withColumn("_ingested_at", F.current_timestamp())

(df.write
   .mode("overwrite")
   .option("overwriteSchema", "true")
   .saveAsTable(fqn))

# Comment + tag for governance lineage in Catalog Explorer
spark.sql(f"""
    COMMENT ON TABLE {fqn} IS
    'Synthetic UK home insurance portfolio — 50,000 policies as the source
     of truth for the radar-databricks demo. Geographic distribution weighted
     to UK population centres (London, Manchester, Birmingham, Leeds, etc.).
     One row per policy. Joined with bronze.flood_overlay in stage 2 to
     produce silver.priced_book_input (the table that goes to Radar).'
""")

print(f"✓ {fqn} — {df.count():,} rows")
