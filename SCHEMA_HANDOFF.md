# Schema handoff — radar-databricks ↔ WTW Radar

This is the contract between Databricks and Radar at Stages 2 and 3.5/3.
Anything inside Databricks (bronze, gold) is internal and can change
freely. The two tables in this document are the boundary — schema changes
on either side need coordination.

---

## INPUT to Radar — `silver.priced_book_input`

Radar reads from this table. It is one row per policy, with the
underwriting fields and the flood overlay already joined.

| Column                   | Type      | Nullable | Description |
|--------------------------|-----------|----------|-------------|
| `policy_id`              | STRING    | NO       | Unique policy identifier (synthetic, format `POL-1000000+`) |
| `postcode_district`      | STRING    | NO       | UK postcode district (e.g. `SW1`, `M1`, `BS1`). Joins back to flood_overlay. |
| `sum_insured`            | LONG      | NO       | Total sum insured (GBP) — buildings + contents |
| `property_type`          | STRING    | NO       | One of: `Detached`, `Semi-Detached`, `Terraced`, `Flat`, `Bungalow` |
| `build_year`             | INT       | NO       | Construction year of the primary building (1880–2025) |
| `occupancy_type`         | STRING    | NO       | One of: `Owner-Occupied`, `Tenanted`, `Holiday Let`, `Vacant` |
| `inception_date`         | DATE      | NO       | Policy inception (UTC) |
| `region`                 | STRING    | NO       | ITL1-style UK region label |
| `flood_zone`             | STRING    | NO       | One of: `1`, `2`, `3a`, `3b` (Environment Agency-style band) |
| `flood_score`            | INT       | NO       | Synthetic flood risk 0–100 |
| `nearest_watercourse`    | STRING    | YES      | Name of nearest river / coast (NULL if no nearby surface water) |
| `distance_to_water_m`    | INT       | YES      | Approx distance from district centroid to watercourse (metres) |
| `centroid_lat`           | DOUBLE    | NO       | Postcode-district centroid latitude (WGS84) |
| `centroid_lng`           | DOUBLE    | NO       | Postcode-district centroid longitude (WGS84) |
| `flood_factor`           | DOUBLE    | NO       | Pricing multiplier 1.0–2.5, derived as `1.0 + flood_score/100 × 1.5` |
| `risk_band`              | STRING    | NO       | One of: `Low`, `Medium`, `High`, `Very High` (mapped from flood_zone) |
| `property_age_band`      | STRING    | NO       | One of: `Pre-1900`, `1900-1949`, `1950-1979`, `1980-1999`, `2000+` |
| `exposure_weighted_score`| DOUBLE    | NO       | `sum_insured × flood_score` — used by Databricks for portfolio analytics |
| `_enriched_at`           | TIMESTAMP | NO       | When the silver row was built (Databricks-side audit) |

**Approx row count:** 50,000

**Production access:** Radar reads via JDBC / Databricks SQL warehouse, or
the table is exported to a Volume as Parquet/CSV depending on the Radar
deployment topology. Either way the schema above is the contract.

---

## OUTPUT from Radar — `silver.priced_book_output`

Radar writes back here. The schema is `priced_book_input` plus four
priced columns. **All columns from the input are passed through
unchanged** — the Databricks side keys back to the input rows on
`policy_id`.

| Column                   | Type      | Nullable | Description |
|--------------------------|-----------|----------|-------------|
| *(all 19 input columns)* |           |          | Pass-through from `priced_book_input`. Same types, same nullability. |
| `premium`                | DOUBLE    | NO       | Charged annual premium (GBP). Includes Radar loadings, expense, and margin. |
| `technical_premium`      | DOUBLE    | NO       | Pure technical price (GBP) — `expected_loss × (1 + expense_loading)` |
| `expected_loss`          | DOUBLE    | NO       | Burning-cost expected annual loss (GBP) |
| `loss_ratio_estimate`    | DOUBLE    | NO       | `expected_loss / premium` — directional indicator only |
| `_priced_at`             | TIMESTAMP | NO       | When the row was priced |
| `_priced_by`             | STRING    | NO       | Identifier of the pricing run (`radar_run:RUNID` or `radar_simulator:RUNID` for demo) |

Radar may add additional columns; Databricks will ignore unknown columns
and they will be visible in Catalog Explorer. The four priced columns
above are the contract.

---

## Audit log — `silver.radar_run_log`

One row per pricing run. Optional but recommended — the demo simulator
writes it; production Radar should mirror the schema.

| Column              | Type      | Description |
|---------------------|-----------|-------------|
| `run_id`            | STRING    | Unique identifier for the pricing run |
| `input_table`       | STRING    | FQN of the table read |
| `output_table`      | STRING    | FQN of the table written |
| `rows_priced`       | INT       | Number of rows priced |
| `total_premium`     | DOUBLE    | Sum of premium across the run (GBP) |
| `total_expected_loss`| DOUBLE   | Sum of expected_loss (GBP) |
| `total_exposure`    | DOUBLE    | Sum of sum_insured (GBP) — sanity check |
| `mean_loss_ratio`   | DOUBLE    | Average loss_ratio_estimate |
| `model_name`        | STRING    | `radar` (production) or `radar_simulator` (demo) |
| `model_version`     | STRING    | Pricing engine version |
| `started_at`        | TIMESTAMP | UTC start time |
| `completed_at`      | TIMESTAMP | UTC completion time |
| `status`            | STRING    | `SUCCESS` / `FAILED` / `PARTIAL` |

---

## Change-management protocol

- Adding a column to the input — Databricks side, no Radar change required.
- Adding a column to the output — Radar side. Databricks ignores by default,
  but tell us so we can surface it in Catalog Explorer + the dashboard.
- Renaming or dropping a column on either side — coordinate. Bump
  `model_version` in `radar_run_log`. Update this document.
- Type changes — coordinate. Same protocol.

The simulator notebook (`src/03_radar_simulator/99_radar_simulator.py`)
mirrors the Radar contract — keep it in sync any time the schema changes,
so the demo continues to work without a real Radar connection.
