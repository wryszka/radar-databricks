#!/usr/bin/env python3
"""Local sample-generator for sanity-checking the synthetic data story.

Mirrors the logic in src/01_bronze/{01,02}_*.py without the Spark/dbutils
plumbing. Stdlib-only so it runs without a venv. Outputs a statistical
summary to stdout. Not part of the bundle — just a dev helper.
"""
import sys
import os
import math
import random
import csv
from collections import Counter, defaultdict
from statistics import mean, median
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "utils"))
from postcode_reference import POSTCODE_DISTRICTS, FLOOD_SCENARIOS  # noqa: E402

SEED = 42
N = 50_000

# ── property_book generation (mirror of 01_generate_property_book.py) ──────
random.seed(SEED)

districts = [r[0] for r in POSTCODE_DISTRICTS]
pop_weights = [r[4] for r in POSTCODE_DISTRICTS]
region_lookup = {r[0]: r[1] for r in POSTCODE_DISTRICTS}

PROPERTY_TYPE_MIX = {
    "London":           [ 4, 12, 28, 52,  4],
    "South East":       [22, 28, 26, 18,  6],
    "South West":       [26, 26, 24, 14, 10],
    "East":             [24, 28, 24, 16,  8],
    "Midlands":         [18, 30, 28, 18,  6],
    "North West":       [14, 28, 32, 20,  6],
    "Yorkshire":        [16, 30, 30, 18,  6],
    "North East":       [14, 30, 32, 18,  6],
    "Wales":            [22, 28, 26, 14, 10],
    "Scotland":         [16, 22, 26, 30,  6],
    "Northern Ireland": [22, 28, 26, 16,  8],
}
PROPERTY_TYPES = ["Detached", "Semi-Detached", "Terraced", "Flat", "Bungalow"]
REGION_SI_BASE = {
    "London": 520, "South East": 420, "South West": 340, "East": 340,
    "Midlands": 260, "North West": 240, "Yorkshire": 230, "North East": 210,
    "Wales": 220, "Scotland": 240, "Northern Ireland": 200,
}
PROPERTY_TYPE_SI_ADJ = {
    "Detached": 1.55, "Semi-Detached": 1.05, "Terraced": 0.85,
    "Flat": 0.70, "Bungalow": 0.95,
}
OCCUPANCY = ["Owner-Occupied", "Tenanted", "Holiday Let", "Vacant"]
OCCUPANCY_WEIGHTS = [76, 20, 3, 1]
today = date(2026, 5, 1)

decade_weights = [
    (1880, 1), (1890, 2), (1900, 4), (1910, 4), (1920, 5), (1930, 8),
    (1940, 3), (1950, 7), (1960, 9), (1970, 9), (1980, 11), (1990, 10),
    (2000, 12), (2010, 10), (2020, 5),
]
decade_starts = [d[0] for d in decade_weights]
decade_w      = [d[1] for d in decade_weights]

policies = []  # list of dicts
for i in range(N):
    pid = f"POL-{1_000_000 + i}"
    district = random.choices(districts, weights=pop_weights, k=1)[0]
    region   = region_lookup[district]
    ptype = random.choices(PROPERTY_TYPES, weights=PROPERTY_TYPE_MIX[region], k=1)[0]
    base = REGION_SI_BASE[region] * PROPERTY_TYPE_SI_ADJ[ptype]
    si_k = round(random.lognormvariate(math.log(base), 0.45))
    sum_insured = max(60, min(si_k, 5000)) * 1000
    dec = random.choices(decade_starts, weights=decade_w, k=1)[0]
    build_year = min(2025, dec + random.randint(0, 9))
    occ = random.choices(OCCUPANCY, weights=OCCUPANCY_WEIGHTS, k=1)[0]
    inception = today - timedelta(days=random.randint(0, 365))
    policies.append({
        "policy_id": pid, "postcode_district": district,
        "sum_insured": sum_insured, "property_type": ptype,
        "build_year": build_year, "occupancy_type": occ,
        "inception_date": inception,
    })

# ── flood_overlay generation ────────────────────────────────────────────
random.seed(SEED)


def derive_flood_zone(score: int) -> str:
    if score >= 75: return "3b"
    if score >= 55: return "3a"
    if score >= 30: return "2"
    return "1"


flood = {}  # district -> dict
for district, region, lat, lng, _pop, flood_base, watercourse, dist_m in POSTCODE_DISTRICTS:
    score = int(round(max(0, min(100, flood_base + random.gauss(0, 4)))))
    flood[district] = {
        "postcode_district": district, "region": region,
        "flood_zone": derive_flood_zone(score), "flood_score": score,
        "nearest_watercourse": watercourse, "distance_to_water_m": dist_m,
        "centroid_lat": lat, "centroid_lng": lng,
    }

# ── REPORT ─────────────────────────────────────────────────────────────────


def hr(title):
    print()
    print("═" * 78)
    print(f"  {title}")
    print("═" * 78)


hr(f"bronze.property_book  ({len(policies):,} rows)")

total_si = sum(p["sum_insured"] for p in policies)
print(f"\nTotal sum insured:   £{total_si / 1e9:,.1f} bn")
print(f"Mean sum insured:    £{int(total_si / len(policies)):,}")
print(f"Median sum insured:  £{int(median(p['sum_insured'] for p in policies)):,}")
print(f"Distinct districts:  {len({p['postcode_district'] for p in policies})}")

# By region
regions = defaultdict(lambda: {"policies": 0, "exposure": 0})
for p in policies:
    r = region_lookup[p["postcode_district"]]
    regions[r]["policies"] += 1
    regions[r]["exposure"] += p["sum_insured"]

print("\nPolicies + exposure by region:")
print(f"  {'region':20s} {'policies':>10s}  {'exposure_bn':>12s}  {'pct_book':>10s}")
for r in sorted(regions, key=lambda k: -regions[k]["exposure"]):
    s = regions[r]
    pct = s["exposure"] / total_si * 100
    print(f"  {r:20s} {s['policies']:>10,}  £{s['exposure'] / 1e9:>10,.1f}bn  {pct:>9.1f}%")

# Property type
ptype_count = Counter(p["property_type"] for p in policies)
print("\nProperty type mix (%):")
for t, c in ptype_count.most_common():
    print(f"  {t:18s} {c / len(policies) * 100:>5.1f}%")

# Occupancy
occ_count = Counter(p["occupancy_type"] for p in policies)
print("\nOccupancy mix (%):")
for t, c in occ_count.most_common():
    print(f"  {t:18s} {c / len(policies) * 100:>5.1f}%")

# Top districts by exposure
district_stats = defaultdict(lambda: {"policies": 0, "exposure": 0})
for p in policies:
    d = p["postcode_district"]
    district_stats[d]["policies"] += 1
    district_stats[d]["exposure"] += p["sum_insured"]

print("\nTop 12 districts by exposure:")
print(f"  {'district':10s} {'region':18s} {'pols':>6s}  {'exp_m':>8s}  {'flood':>6s}  {'zone':>5s}  {'water':30s}")
top = sorted(district_stats.items(), key=lambda kv: -kv[1]["exposure"])[:12]
for d, s in top:
    fo = flood[d]
    print(f"  {d:10s} {fo['region']:18s} {s['policies']:>6,}  £{s['exposure']/1e6:>6,.0f}m  {fo['flood_score']:>6d}  {fo['flood_zone']:>5s}  {str(fo['nearest_watercourse']):30s}")

# ── flood_overlay ──────────────────────────────────────────────────────────
hr(f"bronze.flood_overlay  ({len(flood)} rows)")

print("\nFlood-zone distribution:")
zone_counts = Counter(f["flood_zone"] for f in flood.values())
for z in ["1", "2", "3a", "3b"]:
    print(f"  zone {z:2s}  {zone_counts[z]:>4d}")

print("\nFlood-score by region:")
print(f"  {'region':20s} {'mean':>6s}  {'min':>4s}  {'max':>4s}  {'count':>6s}")
region_scores = defaultdict(list)
for f in flood.values():
    region_scores[f["region"]].append(f["flood_score"])
for r in sorted(region_scores, key=lambda k: -mean(region_scores[k])):
    s = region_scores[r]
    print(f"  {r:20s} {mean(s):>6.1f}  {min(s):>4d}  {max(s):>4d}  {len(s):>6d}")

# High-exposure flood-zone-3 districts (visual punchline on the choropleth)
print("\n🎯 Flood zone 3a/3b districts ranked by exposure (the 'red dots' on the map):")
print(f"  {'district':10s} {'region':18s} {'pols':>6s}  {'exp_m':>8s}  {'flood':>6s}  {'zone':>5s}  {'water':30s}")
hot = []
for d, s in district_stats.items():
    fo = flood[d]
    if fo["flood_zone"] in ("3a", "3b"):
        hot.append((d, s, fo))
for d, s, fo in sorted(hot, key=lambda x: -x[1]["exposure"])[:15]:
    print(f"  {d:10s} {fo['region']:18s} {s['policies']:>6,}  £{s['exposure']/1e6:>6,.0f}m  {fo['flood_score']:>6d}  {fo['flood_zone']:>5s}  {str(fo['nearest_watercourse']):30s}")
total_z3_pols = sum(s["policies"] for d, s, fo in hot)
total_z3_exp = sum(s["exposure"] for d, s, fo in hot)
print(f"\n  Zone-3 total: {total_z3_pols:,} policies, £{total_z3_exp/1e6:,.0f}m ({total_z3_exp/total_si*100:.1f}% of book)")

# Scenario exposure
hr("Scenario-affected exposure (pre-Radar — based on sum_insured only)")
print()
print(f"  {'scenario':30s} {'policies':>9s}  {'exposure':>10s}  {'districts':>9s}  {'pct_book':>8s}")
for name, cfg in FLOOD_SCENARIOS.items():
    affected = [d for d in cfg["districts"] if d in district_stats]
    pols = sum(district_stats[d]["policies"] for d in affected)
    expo = sum(district_stats[d]["exposure"] for d in affected)
    pct = expo / total_si * 100
    print(f"  {name:30s} {pols:>9,}  £{expo/1e6:>7,.0f}m  {len(affected):>9d}  {pct:>7.1f}%")

# Per-district detail for the headline scenario
hr("Thames Valley 1-in-100 — per-district breakdown")
print()
print(f"  {'district':10s} {'pols':>6s}  {'exp_m':>8s}  {'flood':>6s}  {'zone':>5s}")
for d in FLOOD_SCENARIOS["Thames Valley 1-in-100"]["districts"]:
    if d in district_stats:
        s = district_stats[d]
        fo = flood[d]
        print(f"  {d:10s} {s['policies']:>6,}  £{s['exposure']/1e6:>6,.0f}m  {fo['flood_score']:>6d}  {fo['flood_zone']:>5s}")

# Write CSV samples for manual inspection
out_dir = "/tmp"
with open(f"{out_dir}/property_book_sample.csv", "w") as f:
    w = csv.DictWriter(f, fieldnames=list(policies[0].keys()))
    w.writeheader()
    for p in policies[:25]:
        w.writerow(p)
with open(f"{out_dir}/flood_overlay_full.csv", "w") as f:
    w = csv.DictWriter(f, fieldnames=list(next(iter(flood.values())).keys()))
    w.writeheader()
    for v in flood.values():
        w.writerow(v)

print()
print(f"Wrote:")
print(f"  {out_dir}/property_book_sample.csv  (25 rows)")
print(f"  {out_dir}/flood_overlay_full.csv    ({len(flood)} rows)")
