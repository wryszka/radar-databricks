#!/usr/bin/env python3
"""Create the 'Flood Portfolio Q&A' Genie space.

The Lakeview / Genie space creation API is still evolving and the most
reliable path is the Databricks UI. This script emits everything needed for
a 30-second manual setup:

  1. The exact tables to attach
  2. The sample-question list (pre-tested)
  3. The space description / instructions to paste

Run it with --print to see the bundle, or pipe to a YAML file.

Usage:
  scripts/create_genie_space.py \
    --catalog radar_databricks_demo \
    --bronze bronze --silver silver --gold gold

Then in your workspace:
  • New → Genie Space → Add Tables (paste the three FQNs)
  • Description → paste the description block
  • Sample Questions → paste each question on its own line
"""
from __future__ import annotations
import argparse
import json
import os
import sys


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--catalog", default=os.environ.get("CATALOG", "radar_databricks_demo"))
    p.add_argument("--bronze",  default=os.environ.get("BRONZE_SCHEMA", "bronze"))
    p.add_argument("--silver",  default=os.environ.get("SILVER_SCHEMA", "silver"))
    p.add_argument("--gold",    default=os.environ.get("GOLD_SCHEMA", "gold"))
    p.add_argument("--format",  choices=("text", "yaml", "json"), default="text")
    return p.parse_args()


SAMPLE_QUESTIONS = [
    # Headline three (must work cleanly — these drive the demo)
    "Where is our biggest flood exposure?",
    "What's our total exposure in postcodes with flood score above 70?",
    "How does flood concentration compare across regions?",

    # Backup phrasings of each headline (in case the demo deity is angry)
    "Which postcode districts carry the most exposure under flood zones 3a and 3b?",
    "Which district has the highest sum_insured concentrated in flood zone 3?",

    "How much sum insured is in postcodes where flood_score is greater than 70?",
    "Show me total exposure by flood_zone — split by zone band.",

    "Show total exposure and policy count by region, ordered descending.",
    "Which region has the highest mean loss ratio?",

    # Wider exploration
    "What is the top 10 by expected loss?",
    "How many policies are in the Thames Valley 1-in-100 scenario?",
    "What is the scenario loss for each named flood scenario?",
    "Show the largest single sum insured in each region.",
    "Which postcode districts near the Severn carry exposure over £100m?",
    "Compare premium and expected loss for districts in flood zone 3a vs 3b.",
    "Which districts have the highest exposure-weighted flood score?",
]


def main():
    args = parse_args()

    tables = [
        f"{args.catalog}.{args.gold}.flood_concentration",
        f"{args.catalog}.{args.gold}.scenario_results",
        f"{args.catalog}.{args.silver}.priced_book_output",
        f"{args.catalog}.{args.bronze}.flood_overlay",
    ]

    description = (
        "Flood Portfolio Q&A — UK home insurance flood concentration analytics "
        "for the radar-databricks demo. All data is synthetic. The portfolio "
        "is ~50,000 policies across ~150 postcode districts, weighted to UK "
        "population centres. Use this space to ask portfolio-level questions: "
        "where the biggest exposures are, how flood risk concentrates by "
        "region, and what loss looks like under named flood scenarios. "
        "Use postcode_district as the geographic key. flood_zone takes "
        "values '1', '2', '3a', '3b' (3a/3b = flood zone 3, the high-risk "
        "tier). Region is the ITL1-style UK label."
    )

    instructions = (
        "When asked about flood concentration: prefer the gold.flood_concentration "
        "table (one row per postcode district) over silver.priced_book_output "
        "(one row per policy) — concentration is a district-level concept. "
        "When asked about scenarios, use gold.scenario_results. When the user "
        "asks about an individual policy, use silver.priced_book_output. "
        "Express monetary values in £ millions when total exposure exceeds "
        "£10m. Round flood scores to integers."
    )

    bundle = {
        "title": "Flood Portfolio Q&A",
        "description": description,
        "instructions": instructions,
        "tables": tables,
        "sample_questions": SAMPLE_QUESTIONS,
    }

    if args.format == "json":
        print(json.dumps(bundle, indent=2))
        return
    if args.format == "yaml":
        try:
            import yaml
            print(yaml.safe_dump(bundle, sort_keys=False))
        except ImportError:
            sys.exit("yaml not available — install pyyaml or use --format json")
        return

    # text — human-readable copy-paste blocks
    print("=" * 78)
    print("  Flood Portfolio Q&A — Genie space setup")
    print("=" * 78)

    print("\n── Tables to attach ────────────────────────────────────────────")
    for t in tables:
        print(f"  {t}")

    print("\n── Description (paste into the space description) ─────────────")
    print(description)

    print("\n── Instructions (paste into the space instructions / system prompt) ──")
    print(instructions)

    print(f"\n── Sample questions ({len(SAMPLE_QUESTIONS)} pre-tested) ───────────")
    for q in SAMPLE_QUESTIONS:
        print(f"  • {q}")

    print()
    print("=" * 78)
    print(f"  Done. {len(tables)} tables, {len(SAMPLE_QUESTIONS)} sample questions.")
    print("=" * 78)


if __name__ == "__main__":
    main()
