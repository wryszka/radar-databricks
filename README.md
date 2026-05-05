# radar-databricks

A 5-minute IIF demo for **Databricks + WTW Radar — Better Together**, focused
on **UK flood concentration risk** at postcode level.

> **Radar prices each risk. Databricks shows you what those priced risks
> add up to.**

This is a Databricks Asset Bundle (DAB) project. It deploys to any
Databricks workspace with serverless SQL + serverless jobs. All data is
synthetic — no real ABI / EA / customer data is used.

## About this demo

Synthetic. Demo-grade. The portfolio is 50,000 fake UK home-insurance
policies; the flood overlay is hand-curated to be geographically
plausible (Thames Valley, Severn, Trent, Calder/Aire, East Anglian fens,
south-coast surge zones all elevated) but no real Environment Agency
flood map data is used.

Stage 3 of the four-stage flow is the WTW Radar pricing run — in the
demo this is a pre-recorded video; for self-contained redeployment a
notebook (`99_radar_simulator.py`, clearly named) stands in.

## The four-stage flow

```
   Stage 1: Ingest          Stage 2: Enrich           Stage 3: Radar      Stage 4: Aggregate
   ───────────────          ──────────────            ───────────         ──────────────────
   bronze.property_book ──▶ silver.priced_book_input ─┐
   bronze.flood_overlay ──▶                            │
                                                       ▼
                                              ┌───────────────┐
                                              │  WTW Radar    │ (pre-recorded video)
                                              │   pricing     │ — or 99_radar_simulator
                                              └───────┬───────┘    for self-contained runs
                                                      │
                                                      ▼
                                          silver.priced_book_output
                                                      │
                                                      ▼
                                          gold.flood_concentration
                                          gold.scenario_results
```

| Stage | Notebook(s) | Output |
|---|---|---|
| 1 — Ingest | `src/01_bronze/01_generate_property_book.py`, `02_generate_flood_overlay.py` | `bronze.property_book`, `bronze.flood_overlay` |
| 2 — Enrich | `src/02_silver/01_priced_book_input.sql` | `silver.priced_book_input` |
| 3 — Radar (pre-recorded video, or simulator) | `src/03_radar_simulator/99_radar_simulator.py` | `silver.priced_book_output` |
| 4 — Aggregate | `src/04_gold/01_flood_concentration.sql`, `02_scenario_results.py` | `gold.flood_concentration`, `gold.scenario_results` |

## Quick start

```bash
# 1. Clone
git clone https://github.com/wryszka/radar-databricks.git
cd radar-databricks

# 2. Configure databricks.yml — uncomment the workspace block and point
#    `host` + `profile` at your workspace. Optionally override the catalog
#    name via --var on the CLI.

databricks bundle deploy -p YOUR_PROFILE \
  --var="catalog_name=radar_databricks_demo"

# 3. Run setup + the full demo pipeline
databricks bundle run setup_demo      -p YOUR_PROFILE
databricks bundle run run_full_demo   -p YOUR_PROFILE

# 4. Create the Lakeview dashboard
python3 scripts/create_dashboard.py \
  --warehouse-id YOUR_WAREHOUSE_ID \
  --parent-path  /Users/your.email@databricks.com \
  --profile      YOUR_PROFILE

# 5. Set up the Genie space (manual — emit the config first)
python3 scripts/create_genie_space.py
#   → paste the tables, description, and sample questions into a new
#     Genie space via the Databricks UI
```

To rebuild from scratch without redeploying:
```bash
databricks bundle run run_full_demo -p YOUR_PROFILE
```

## Repository layout

```
├── databricks.yml              # bundle config (catalog + schemas as variables)
├── README.md                   # this file
├── DEMO_SCRIPT.md              # 5-minute roleplay script (Laurence + Connor)
├── SCHEMA_HANDOFF.md           # input/output schema contract at the Radar boundary
├── resources/                  # one job per stage + the orchestrator
│   ├── setup_job.yml
│   ├── stage1_ingest.yml
│   ├── stage2_enrich.yml
│   ├── stage3_5_radar_sim.yml
│   ├── stage4_aggregate.yml
│   ├── full_pipeline.yml
│   └── apply_metadata.yml
├── src/
│   ├── 00_setup/               # catalog + schemas, descriptions, full-demo orchestrator
│   ├── 01_bronze/              # synthetic data generators
│   ├── 02_silver/              # geospatial join — INPUT to Radar
│   ├── 03_radar_simulator/     # 99_radar_simulator.py (DEMO AID — not production)
│   ├── 04_gold/                # portfolio aggregation + scenario stress
│   └── utils/                  # shared postcode / region / scenario reference data
└── scripts/
    ├── create_dashboard.py     # Lakeview 'Flood Concentration View'
    ├── create_genie_space.py   # 'Flood Portfolio Q&A' (emits config for manual setup)
    └── _local_sample.py        # dev helper — generates a sample without Spark
```

## Tables

```
catalog: radar_databricks_demo (configurable)

bronze.property_book                ~50,000 rows  one per policy
bronze.flood_overlay                ~150 rows     one per postcode district
silver.priced_book_input            ~50,000 rows  geospatial join — INPUT TO RADAR
silver.priced_book_output           ~50,000 rows  Radar's output (priced book)
silver.radar_run_log                growing       one row per pricing run
gold.flood_concentration            ~150 rows     district-level aggregation
gold.scenario_results               5 rows        one per named flood scenario
gold.scenario_district_detail       ~40 rows      per-(scenario, district) drill-down
```

## Governance

Every table has a `COMMENT ON TABLE`. Every key column has a column comment.
The Radar boundary tables (`silver.priced_book_input` and
`silver.priced_book_output`) are tagged `radar_boundary=input/output` for
discovery in Catalog Explorer. Re-run `databricks bundle run apply_metadata`
any time after a schema change.

## Prerequisites

- Databricks workspace with **serverless SQL + serverless jobs**
- Unity Catalog enabled
- Databricks CLI v0.200+
- A SQL warehouse for the dashboard

## Disclaimer

Synthetic demonstration. All postcodes, policies, flood scores, and named
scenarios are fictional or hand-curated for the demo. No real customer
data, real EA flood map data, or real ABI data is used. Pricing logic in
`99_radar_simulator.py` is deliberately simple — in production it is
replaced by WTW Radar.
