-- Databricks notebook source
-- MAGIC %md
-- MAGIC # Stage 4 — gold.flood_concentration
-- MAGIC
-- MAGIC Per-postcode-district aggregation of the priced book. This is the
-- MAGIC primary table behind the Lakeview map and the top-10 accumulation
-- MAGIC table. Idempotent — replaces in place on every run.

-- COMMAND ----------

CREATE WIDGET TEXT catalog_name  DEFAULT 'radar_databricks_demo';
CREATE WIDGET TEXT silver_schema DEFAULT 'silver';
CREATE WIDGET TEXT gold_schema   DEFAULT 'gold';

-- COMMAND ----------

CREATE OR REPLACE TABLE
  IDENTIFIER(:catalog_name || '.' || :gold_schema || '.flood_concentration')
COMMENT 'Per-postcode-district concentration view — total exposure, premium, expected loss, policy count, max single risk, plus the flood overlay (zone, score, region, watercourse, centroid). Primary table for the Lakeview map and accumulation table.'
AS
SELECT
  postcode_district,
  region,
  flood_zone,
  flood_score,
  nearest_watercourse,
  centroid_lat,
  centroid_lng,
  COUNT(*)                          AS policy_count,
  SUM(sum_insured)                  AS total_exposure,
  MAX(sum_insured)                  AS max_single_risk,
  ROUND(AVG(sum_insured))           AS avg_sum_insured,
  SUM(premium)                      AS total_premium,
  SUM(expected_loss)                AS total_expected_loss,
  ROUND(AVG(loss_ratio_estimate), 4) AS mean_loss_ratio,
  -- exposure-weighted flood score (validates the choropleth colouring)
  ROUND(SUM(exposure_weighted_score) / SUM(sum_insured), 1)
                                    AS exposure_weighted_flood_score
FROM
  IDENTIFIER(:catalog_name || '.' || :silver_schema || '.priced_book_output')
GROUP BY
  postcode_district, region, flood_zone, flood_score,
  nearest_watercourse, centroid_lat, centroid_lng;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Top 10 districts by exposure — sanity check

-- COMMAND ----------

SELECT
  postcode_district, region, flood_zone, flood_score,
  policy_count,
  ROUND(total_exposure / 1e6, 1)        AS exposure_m,
  ROUND(total_premium / 1e6, 2)         AS premium_m,
  ROUND(total_expected_loss / 1e3, 1)   AS expected_loss_k,
  ROUND(mean_loss_ratio * 100, 2)       AS loss_ratio_pct
FROM IDENTIFIER(:catalog_name || '.' || :gold_schema || '.flood_concentration')
ORDER BY total_exposure DESC
LIMIT 10;
