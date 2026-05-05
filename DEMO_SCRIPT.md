# Demo script — IIF: Databricks + WTW Radar (Better Together)

5 minutes. Roleplay between **Laurence** (Databricks data team) and
**Connor** (WTW Radar, pre-recorded video). UK pricing-actuary audience.

The whole demo is one story: **"Radar prices each risk. Databricks shows
you what those priced risks add up to."**

---

## Pre-flight checklist (do this before walking on stage)

- [ ] Workspace open in browser, signed in
- [ ] Lakeview dashboard `Flood Concentration View` published, refreshed
- [ ] Genie space `Flood Portfolio Q&A` open in another tab
- [ ] Catalog Explorer showing `radar_databricks_demo` schemas tab
- [ ] Connor's pre-recorded Radar video pre-loaded, queued at 0:00
- [ ] Mic check, lavalier on, click-through rehearsed once

If you run into issues:
```bash
databricks bundle run run_full_demo -p YOUR_PROFILE   # full rebuild ~3 min
```

---

## Timing

| Time | Stage | Owner |
|---|---|---|
| 0:00 – 0:30 | Setup the story | Laurence |
| 0:30 – 1:00 | **Stage 1** — Ingest | Laurence |
| 1:00 – 1:30 | **Stage 2** — Enrich | Laurence |
| 1:30 – 2:30 | **Stage 3** — Radar (pre-recorded) | Connor (video) |
| 2:30 – 4:30 | **Stage 4** — Aggregate / Analyse | Laurence |
| 4:30 – 5:00 | The "Better Together" wrap | Laurence |

---

## 0:00 – 0:30 — Setup

> **Laurence (to audience):** "Pricing actuaries — you're already brilliant
> at pricing the *individual* risk. Radar gives you that. What we want to
> show in the next five minutes is what happens *after* every risk has been
> priced, when you want to see the portfolio. Where are the
> concentrations? What does one flood scenario do to the book? Connor and I
> are going to walk through it. He owns the pricing step. I own everything
> on either side of it."

(Click to Catalog Explorer → `radar_databricks_demo`.)

---

## 0:30 – 1:00 — Stage 1: Ingest

> **Laurence:** "Two things land in our bronze schema. The first is the
> book itself — 50,000 UK home insurance policies, postcode-district
> granularity, sums insured, build year, occupancy. The second is a flood
> overlay — one row per postcode district, with a flood score and an
> Environment Agency-style zone band. Click into either table and you can
> see the descriptions, the column comments, and Unity Catalog lineage.
> Standard Databricks medallion — bronze, silver, gold."

(Click into `bronze.property_book` → show table preview. Click into
`bronze.flood_overlay` → show flood_zone column.)

---

## 1:00 – 1:30 — Stage 2: Enrich

> **Laurence:** "Stage 2 is one SQL notebook. It joins the policy book
> against the flood overlay on postcode district, derives a flood factor,
> a risk band, an age band — and writes `silver.priced_book_input`. This
> is the table that *goes to Radar*. The schema is locked — we have a
> handoff document with the Radar team that defines exactly which columns
> live at this boundary. Connor — over to you."

(Click into `silver.priced_book_input` → show the schema briefly.
Hand off to Connor's video.)

---

## 1:30 – 2:30 — Stage 3: Radar (pre-recorded video)

> **Connor (video):** [Whatever Connor says — Radar reads
> `priced_book_input`, applies the rated technical price, and produces
> `priced_book_output`.]

When the video ends, Laurence picks back up. The output table
`silver.priced_book_output` already exists in the workspace (because the
simulator notebook ran during setup), so the handoff feels seamless.

---

## 2:30 – 4:30 — Stage 4: Aggregate / Analyse  *(the punchline)*

> **Laurence:** "Connor's done his part — every risk has a price.
> `silver.priced_book_output` now carries premium, technical premium,
> expected loss for every policy. The interesting question for the
> portfolio team is what those add up to. Click."

(Open the Lakeview dashboard `Flood Concentration View`.)

### Talk to the KPI tiles (~15s)
> "**£18bn of exposure** across 50,000 policies. £45m of premium.
> **20.7% of the book sits in flood zone 3** — that's the headline number
> for portfolio risk."

### Talk to the map (~30s — the centrepiece)
> "Every bubble is a postcode district. Size is exposure, colour is flood
> score — red is high. London core is all blue, thanks to the Thames
> Barrier. But look at the cluster *here* —" *(point at TW9, TW10, TW11,
> KT1, KT2 — west London / Thames-adjacent)* "— Richmond, Teddington,
> Kingston. Five districts, £1.2bn of exposure, all flood zone 3a/3b.
> That's the kind of concentration that doesn't show up if you're looking
> at premium per risk in Radar — but it lights up the moment you look at
> the *book*."

### Talk to the top-10 table (~15s)
> "Same story in tabular form. Top 15 districts by exposure — five of them
> are zone 3."

### Talk to the scenario tile (~30s — the second punchline)
> "Three named flood scenarios. **Thames Valley 1-in-100** — that's the
> one that hits the Richmond / Kingston cluster — applies a 6.5× severity
> multiplier and produces a single-event loss of about **£10m**, against
> £5m of premium across those districts. The 'loss-to-premium' ratio is
> 200% — one event eats two years of premium for that cluster.
> **East Coast Surge** — Hull, King's Lynn, Norwich — different severity,
> different geography. **Severn Winter Floods** — Gloucester, Worcester,
> Shrewsbury."

### Switch to Genie (~30s)
> "And because every table has descriptions, tags, and column comments,
> we get a Genie space for free. Pricing actuaries can ask portfolio
> questions in English."

(Tab to Genie. Run two of these:)

1. **"Where is our biggest flood exposure?"** → Genie returns the
   ranked postcode districts.
2. **"What's our total exposure in postcodes with flood score above 70?"**
   → Genie returns a single number.

(If a question doesn't land cleanly, fall back to:)

> **Backup q1:** *"Which postcode districts carry the most exposure
> under flood zones 3a and 3b?"*
> **Backup q2:** *"How much sum insured is in postcodes where flood_score
> is greater than 70?"*

---

## 4:30 – 5:00 — Better Together

> **Laurence:** "Connor's Radar gave us the technical price for every
> individual risk. Databricks gave us the lineage in, the geospatial
> enrichment, the place to land Radar's output, the portfolio
> aggregation, the map, the scenario stress, and the Genie space. Same
> story, two halves. **Radar prices each risk. Databricks shows you what
> those priced risks add up to.** Thank you."

---

## Slot for Connor's Radar video

The video sits between Stage 2 and Stage 4 (1:30 – 2:30 in the timing
above). Recommended runtime: **45–60 seconds**. The on-screen narrative
should:

- Open with `silver.priced_book_input` schema visible
- Show Radar reading the input
- Show the rating engine producing technical price + expected loss
- End with `silver.priced_book_output` schema visible

The exact column contract is in `SCHEMA_HANDOFF.md`.

---

## If everything breaks

```bash
# Full rebuild — everything from scratch, ~3 minutes on serverless:
databricks bundle run run_full_demo -p YOUR_PROFILE
```

Sample-only fallback for the data conversation if the workspace is offline:
```bash
python3 scripts/_local_sample.py   # stdlib-only, prints the punchline numbers
```
