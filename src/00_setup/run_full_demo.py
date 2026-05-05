# Databricks notebook source
# MAGIC %md
# MAGIC # Run Full Demo Pipeline
# MAGIC
# MAGIC Orchestrates the four-stage flow end-to-end:
# MAGIC
# MAGIC 1. **Stage 1 — Ingest** (bronze.property_book + bronze.flood_overlay)
# MAGIC 2. **Stage 2 — Enrich** (silver.priced_book_input ← input to Radar)
# MAGIC 3. **Stage 3.5 — Radar Simulator** (silver.priced_book_output ← demo aid)
# MAGIC 4. **Stage 4 — Aggregate** (gold.flood_concentration + gold.scenario_results)
# MAGIC
# MAGIC Stage 3 (the actual Radar pricing run) is **not** part of this orchestrator —
# MAGIC in production it's the integration point with WTW Radar; for demo
# MAGIC purposes the simulator notebook stands in.

# COMMAND ----------

dbutils.widgets.text("catalog_name",  "radar_databricks_demo")
dbutils.widgets.text("bronze_schema", "bronze")
dbutils.widgets.text("silver_schema", "silver")
dbutils.widgets.text("gold_schema",   "gold")

catalog = dbutils.widgets.get("catalog_name")
bronze  = dbutils.widgets.get("bronze_schema")
silver  = dbutils.widgets.get("silver_schema")
gold    = dbutils.widgets.get("gold_schema")

base_params = {
    "catalog_name":  catalog,
    "bronze_schema": bronze,
    "silver_schema": silver,
    "gold_schema":   gold,
}

# COMMAND ----------

# MAGIC %md
# MAGIC ## Stage 1 — Ingest

# COMMAND ----------

dbutils.notebook.run("../01_bronze/01_generate_property_book", 600, base_params)
print("✓ bronze.property_book")

dbutils.notebook.run("../01_bronze/02_generate_flood_overlay", 600, base_params)
print("✓ bronze.flood_overlay")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Stage 2 — Enrich

# COMMAND ----------

dbutils.notebook.run("../02_silver/01_priced_book_input", 600, base_params)
print("✓ silver.priced_book_input  (handoff to Radar)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Stage 3.5 — Radar Simulator (demo aid)

# COMMAND ----------

dbutils.notebook.run("../03_radar_simulator/99_radar_simulator", 600, base_params)
print("✓ silver.priced_book_output  (deposited by Radar simulator)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Stage 4 — Aggregate

# COMMAND ----------

dbutils.notebook.run("../04_gold/01_flood_concentration", 600, base_params)
print("✓ gold.flood_concentration")

dbutils.notebook.run("../04_gold/02_scenario_results", 600, base_params)
print("✓ gold.scenario_results")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Stage 5 — Apply metadata (table + column comments + tags)
# MAGIC Done at the end so comments land on real tables, not on no-op skips.

# COMMAND ----------

dbutils.notebook.run("apply_metadata", 600, base_params)
print("✓ governance metadata applied")

# COMMAND ----------

print(f"""
═══════════════════════════════════════════════════════════════
  Full demo pipeline complete.

  Bronze: {catalog}.{bronze}.property_book
          {catalog}.{bronze}.flood_overlay
  Silver: {catalog}.{silver}.priced_book_input    ← to Radar
          {catalog}.{silver}.priced_book_output   ← from Radar
  Gold:   {catalog}.{gold}.flood_concentration
          {catalog}.{gold}.scenario_results

  Open the Lakeview dashboard 'Flood Concentration View' and the
  Genie space 'Flood Portfolio Q&A' to drive the demo.
═══════════════════════════════════════════════════════════════
""")
