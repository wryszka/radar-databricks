-- Databricks notebook source
-- MAGIC %md
-- MAGIC # Stage 2 — silver.priced_book_input
-- MAGIC
-- MAGIC The geospatial join: every policy in `bronze.property_book` enriched
-- MAGIC with the flood overlay for its postcode district. This is the table
-- MAGIC that "goes to Radar" — it's the input to the pricing run.
-- MAGIC
-- MAGIC Schema is locked: any change here must be coordinated with the Radar
-- MAGIC team (see SCHEMA_HANDOFF.md). Idempotent — re-runs replace.

-- COMMAND ----------

CREATE WIDGET TEXT catalog_name  DEFAULT 'radar_databricks_demo';
CREATE WIDGET TEXT bronze_schema DEFAULT 'bronze';
CREATE WIDGET TEXT silver_schema DEFAULT 'silver';

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Build the priced-book input
-- MAGIC
-- MAGIC Derived columns:
-- MAGIC - **flood_factor** — pricing multiplier (1.0–2.5) keyed off flood_score
-- MAGIC - **risk_band** — Low / Medium / High / Very High from flood_zone
-- MAGIC - **property_age_band** — actuarial age cohort
-- MAGIC - **exposure_weighted_score** — flood_score × sum_insured (used by gold)

-- COMMAND ----------

CREATE OR REPLACE TABLE
  IDENTIFIER(:catalog_name || '.' || :silver_schema || '.priced_book_input')
COMMENT 'Stage 2 — geospatial join of property_book × flood_overlay. THIS IS THE INPUT TO RADAR. Schema must stay stable; coordinate any change with the pricing team.'
AS
SELECT
  -- ── Policy fields (unchanged from bronze.property_book) ────────────────
  pb.policy_id,
  pb.postcode_district,
  pb.sum_insured,
  pb.property_type,
  pb.build_year,
  pb.occupancy_type,
  pb.inception_date,

  -- ── Flood overlay fields ───────────────────────────────────────────────
  fo.region,
  fo.flood_zone,
  fo.flood_score,
  fo.nearest_watercourse,
  fo.distance_to_water_m,
  fo.centroid_lat,
  fo.centroid_lng,

  -- ── Derived features for pricing + analytics ───────────────────────────
  -- flood_factor: smooth multiplier 1.0–2.5 from flood_score
  ROUND(1.0 + (fo.flood_score / 100.0) * 1.5, 4)                AS flood_factor,

  -- risk_band: ordinal label, derived from flood_zone
  CASE fo.flood_zone
    WHEN '1'  THEN 'Low'
    WHEN '2'  THEN 'Medium'
    WHEN '3a' THEN 'High'
    WHEN '3b' THEN 'Very High'
  END                                                            AS risk_band,

  -- property_age_band: actuarial age cohorts (year_of_data = 2026)
  CASE
    WHEN pb.build_year < 1900 THEN 'Pre-1900'
    WHEN pb.build_year < 1950 THEN '1900-1949'
    WHEN pb.build_year < 1980 THEN '1950-1979'
    WHEN pb.build_year < 2000 THEN '1980-1999'
    ELSE                            '2000+'
  END                                                            AS property_age_band,

  -- exposure_weighted_score: used by gold.flood_concentration to compute
  -- portfolio-level weighted flood score
  CAST(pb.sum_insured AS DOUBLE) * fo.flood_score                AS exposure_weighted_score,

  current_timestamp()                                            AS _enriched_at
FROM
  IDENTIFIER(:catalog_name || '.' || :bronze_schema || '.property_book') pb
INNER JOIN
  IDENTIFIER(:catalog_name || '.' || :bronze_schema || '.flood_overlay')   fo
  ON pb.postcode_district = fo.postcode_district;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Sanity check — row count + schema preview

-- COMMAND ----------

SELECT COUNT(*)                                AS row_count,
       SUM(sum_insured) / 1e9                  AS total_exposure_bn,
       AVG(flood_factor)                       AS mean_flood_factor,
       SUM(CASE WHEN flood_zone IN ('3a','3b') THEN sum_insured END) / SUM(sum_insured) * 100
                                               AS pct_book_in_zone3
FROM IDENTIFIER(:catalog_name || '.' || :silver_schema || '.priced_book_input');
