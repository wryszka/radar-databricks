# Demo day — operational runbook

How to actually run this on stage. Companion to `DEMO_SCRIPT.md` (which has
the narrative and dialogue). This file is for everything else: URLs,
click order, recovery commands.

## Live deployment

| Asset | URL |
|---|---|
| **Dashboard — Flood Concentration View** | https://fevm-lr-serverless-aws-us.cloud.databricks.com/dashboardsv3/01f1487b844416c88218cb82d3be5fea |
| **Genie — Flood Portfolio Q&A** | https://fevm-lr-serverless-aws-us.cloud.databricks.com/genie/rooms/01f1487cc0bc1af1b06e394546b95181 |
| **Catalog Explorer (radar_gold)** | https://fevm-lr-serverless-aws-us.cloud.databricks.com/explore/data/lr_serverless_aws_us_catalog/radar_gold |
| **Catalog Explorer (radar_silver)** | https://fevm-lr-serverless-aws-us.cloud.databricks.com/explore/data/lr_serverless_aws_us_catalog/radar_silver |
| **Catalog Explorer (radar_bronze)** | https://fevm-lr-serverless-aws-us.cloud.databricks.com/explore/data/lr_serverless_aws_us_catalog/radar_bronze |
| **Workspace files** | https://fevm-lr-serverless-aws-us.cloud.databricks.com/#workspace/Workspace/Users/laurence.ryszka@databricks.com/.bundle/radar-databricks/dev/files |
| **Job — full pipeline** | https://fevm-lr-serverless-aws-us.cloud.databricks.com/?o=7474659673789953#job/946549576436613 |
| **GitHub** | https://github.com/wryszka/radar-databricks |

**Workspace:** `fevm-lr-serverless-aws-us.cloud.databricks.com`
**Catalog:** `lr_serverless_aws_us_catalog`
**Schemas:** `radar_bronze`, `radar_silver`, `radar_gold`
**Warehouse:** `ab79eced8207d29b` (serverless PRO — used by the dashboard)
**Profile:** `DEFAULT`

---

## Genie space — already deployed

The Genie space is live at the URL above. It carries:
- 5 tables: `flood_concentration`, `scenario_results`, `scenario_district_detail`,
  `priced_book_output`, `flood_overlay`
- 9 curated sample questions (the headline three plus backup phrasings)
- 5 general instructions (district-level table, scenario_results, flood zones,
  money formatting, geographic key)

To redeploy from scratch (e.g. on a fresh workspace) or rebuild the curated
content if it gets out of sync:

```bash
# Create + populate from scratch
python3 scripts/create_genie_space.py \
  --catalog lr_serverless_aws_us_catalog \
  --bronze radar_bronze --silver radar_silver --gold radar_gold \
  --warehouse-id ab79eced8207d29b \
  --parent-path /Workspace/Users/laurence.ryszka@databricks.com \
  --profile DEFAULT

# Or, add curated content to an existing empty space
python3 scripts/create_genie_space.py \
  --catalog lr_serverless_aws_us_catalog \
  --bronze radar_bronze --silver radar_silver --gold radar_gold \
  --space-id 01f1487cc0bc1af1b06e394546b95181 \
  --profile DEFAULT
```

**Test the headline three questions before walking on stage:**
1. *"Where is our biggest flood exposure?"*
2. *"What's our total exposure in postcodes with flood score above 70?"*
3. *"How does flood concentration compare across regions?"*

If any answer is wrong, the instructions can be edited live in the Genie UI
(*Settings → Instructions* on the space).

---

## Pre-flight checklist (do this 5 min before going on stage)

- [ ] Browser: open the **dashboard** URL above. Confirm it renders. Confirm
      the map shows bubbles. Confirm KPI tiles show numbers (not "—").
- [ ] Browser: open **Catalog Explorer** for `radar_gold`. Confirm 4 tables
      visible with descriptions on hover.
- [ ] Browser: open the **Genie space** (once created above). Refresh.
- [ ] Open Connor's pre-recorded Radar video in another tab, queued at 0:00.
- [ ] Ctrl/Cmd-Shift-T order in the browser so tabs cycle: Catalog → Bronze
      → Silver Input → (Connor video) → Dashboard → Genie. Match `DEMO_SCRIPT.md`.
- [ ] Mic check, lavalier on.

If anything looks wrong, run the rebuild block below.

---

## Click order during the demo (matches `DEMO_SCRIPT.md`)

| Time | What to click | What's on screen |
|---|---|---|
| 0:00 | Catalog Explorer → `lr_serverless_aws_us_catalog` | The catalog with three radar_* schemas |
| 0:30 | `radar_bronze.property_book` | Table preview, descriptions visible |
| 0:45 | `radar_bronze.flood_overlay` | Table preview, flood_zone column visible |
| 1:00 | `radar_silver.priced_book_input` | The handoff schema (lock this with Connor) |
| 1:30 | Switch to Connor's video, play | Pre-recorded Radar pricing |
| 2:30 | Dashboard tab — `Flood Concentration View` | KPI strip + map |
| 2:45 | Hover the map — point at TW9/TW10/TW11/KT1 cluster | The "didn't realise we had that much there" moment |
| 3:15 | Scroll down to the **Top 15 by Exposure** table | Five zone-3 rows in there |
| 3:45 | Scroll down to the **Scenario** table | "Thames Valley 1-in-100 = 198.6% loss/premium" |
| 4:15 | Switch to Genie tab | Type the headline question |
| 4:45 | Wrap | "Radar prices each risk. Databricks shows you what those priced risks add up to." |

---

## Headline numbers to commit to memory

These are the numbers that make the demo land. They come from the live
data in the workspace right now.

| Headline | Value |
|---|---|
| Total book | **£18.1bn** across **50,000 policies** in **154 postcode districts** |
| % book in flood zone 3 (a/b) | **20.7%** (£3.74bn / 9,380 policies) |
| Top zone-3 district | **KT1 (Kingston)** — £265m exposure, flood 68, zone 3a |
| Surprise cluster | **TW9 / TW10 / TW11 / KT1 / KT2** (west London / Thames-adjacent) — £1.18bn combined, all zone 3a/3b |
| **Thames Valley 1-in-100 scenario** | **£18.5m** scenario loss vs **£9.3m** premium → **198.6%** loss/premium |
| East Coast Surge | £4.6m loss vs £2.1m premium → **219.6%** loss/premium |
| Severn Winter Floods | £3.8m loss vs £2.2m premium → **172.2%** loss/premium |

The 198.6% number is the demo punchline. **One Thames Valley 1-in-100 event
eats 2× the premium for that cluster.**

---

## If something breaks on stage

### Dashboard tile shows "—" or empty
The dashboard query failed. Click "Refresh" on the tile. If still empty,
the underlying table is empty (probably mid-rebuild). Run:
```bash
databricks --profile DEFAULT bundle run run_full_demo -t dev
```
This rebuilds everything from scratch in ~5 min.

### Genie returns the wrong answer
Try the backup phrasing for that question (see `DEMO_SCRIPT.md` for the
list). If still wrong, fall back to the dashboard for the same data point.

### Map widget renders blank
The symbol-map widget occasionally takes 5–10s to load on cold start.
Click into a different tab, then back to the dashboard. If still blank,
re-publish the dashboard:
```bash
python3 scripts/create_dashboard.py \
  --catalog lr_serverless_aws_us_catalog \
  --gold-schema radar_gold \
  --silver-schema radar_silver \
  --warehouse-id ab79eced8207d29b \
  --profile DEFAULT \
  --update 01f1487b844416c88218cb82d3be5fea
```

### Total nuclear option (full rebuild, ~5 min)
```bash
cd /Users/laurence.ryszka/vibe/radar-databricks
databricks --profile DEFAULT bundle deploy -t dev
databricks --profile DEFAULT bundle run setup_demo -t dev
databricks --profile DEFAULT bundle run run_full_demo -t dev
```

### Workspace is offline / no internet
Run the stdlib-only sample script — it produces the same headline numbers
without Databricks:
```bash
python3 scripts/_local_sample.py
```
Use the printed output as a fallback narrative reference.

---

## Re-running between demos

Between demo runs, the data is idempotent — `run_full_demo` re-builds in
place. No teardown needed. The data is deterministic (seed=42), so the
numbers above will be identical every run.

---

## Teardown (when this demo's lifecycle is over)

```bash
databricks --profile DEFAULT bundle destroy -t dev --auto-approve
# Then drop the schemas:
databricks --profile DEFAULT api post /api/2.0/sql/statements \
  --json '{"warehouse_id": "ab79eced8207d29b", "statement": "DROP SCHEMA lr_serverless_aws_us_catalog.radar_bronze CASCADE; DROP SCHEMA lr_serverless_aws_us_catalog.radar_silver CASCADE; DROP SCHEMA lr_serverless_aws_us_catalog.radar_gold CASCADE;"}'
# Then delete the dashboard:
databricks --profile DEFAULT api delete /api/2.0/lakeview/dashboards/01f1487b844416c88218cb82d3be5fea
# Genie space — delete via the UI.
```
