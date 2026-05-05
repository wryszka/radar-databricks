# Databricks notebook source
# MAGIC %md
# MAGIC # Setup — Radar × Databricks Demo
# MAGIC
# MAGIC Creates the catalog (if permission allows) and the bronze / silver / gold
# MAGIC schemas used by the demo. Idempotent — safe to re-run.

# COMMAND ----------

dbutils.widgets.text("catalog_name",  "radar_databricks_demo")
dbutils.widgets.text("bronze_schema", "bronze")
dbutils.widgets.text("silver_schema", "silver")
dbutils.widgets.text("gold_schema",   "gold")

catalog = dbutils.widgets.get("catalog_name")
bronze  = dbutils.widgets.get("bronze_schema")
silver  = dbutils.widgets.get("silver_schema")
gold    = dbutils.widgets.get("gold_schema")

print(f"Catalog: {catalog}")
print(f"Bronze:  {catalog}.{bronze}")
print(f"Silver:  {catalog}.{silver}")
print(f"Gold:    {catalog}.{gold}")

# COMMAND ----------

# Try to create the catalog. If we don't have CREATE CATALOG, fall back to
# assuming it already exists.
try:
    spark.sql(f"CREATE CATALOG IF NOT EXISTS {catalog}")
    print(f"✓ catalog {catalog}")
except Exception as e:
    print(f"  [skip] CREATE CATALOG {catalog} — assuming it exists. ({str(e)[:120]})")

for s in (bronze, silver, gold):
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog}.{s}")
    print(f"✓ schema {catalog}.{s}")

# COMMAND ----------

print(f"""
Setup complete.
  Catalog:  {catalog}
  Schemas:  {bronze}, {silver}, {gold}

  Next:
    databricks bundle run stage1_ingest      # bronze.property_book + bronze.flood_overlay
    databricks bundle run stage2_enrich      # silver.priced_book_input
    databricks bundle run stage3_5_radar_simulator  # silver.priced_book_output (DEMO AID)
    databricks bundle run stage4_aggregate   # gold.flood_concentration + gold.scenario_results

  Or in one shot:
    databricks bundle run run_full_demo
""")
