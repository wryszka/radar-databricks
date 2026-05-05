#!/usr/bin/env python3
"""Create + configure the 'Flood Portfolio Q&A' Genie space programmatically.

Uses the same shape that solvency-ii-qrt-demo-pnc/deploy_demo.sh proved
works in production:

    POST /api/2.0/genie/spaces       — create the space (tables + warehouse)
    POST /api/2.0/data-rooms/{id}/curated-questions  — add sample questions
    POST /api/2.0/data-rooms/{id}/instructions       — add general instructions

Both endpoints (genie/spaces and data-rooms/{id}/...) point at the same
underlying object — the data-rooms endpoint is what the Genie UI hits to
manage the space's curated content. The IDs are interchangeable.

Usage:
  scripts/create_genie_space.py \\
    --catalog lr_serverless_aws_us_catalog \\
    --bronze radar_bronze --silver radar_silver --gold radar_gold \\
    --warehouse-id ab79eced8207d29b \\
    --parent-path /Workspace/Users/your.email@databricks.com \\
    --profile DEFAULT
"""
from __future__ import annotations
import argparse
import json
import os
import subprocess
import sys


SAMPLE_QUESTIONS = [
    "Where is our biggest flood exposure?",
    "What's our total exposure in postcodes with flood score above 70?",
    "How does flood concentration compare across regions?",
    "Which postcode districts carry the most exposure under flood zones 3a and 3b?",
    "Which district has the highest sum_insured concentrated in flood zone 3?",
    "How much sum insured is in postcodes where flood_score is greater than 70?",
    "What is the top 10 by expected loss?",
    "How many policies are in the Thames Valley 1-in-100 scenario?",
    "What is the scenario loss for each named flood scenario?",
]

INSTRUCTIONS = [
    {
        "title": "Use district-level table for concentration questions",
        "content": (
            "When the user asks about flood concentration, exposure by district, or "
            "'where is our biggest exposure', prefer the gold.flood_concentration "
            "table (one row per postcode district) over silver.priced_book_output "
            "(one row per policy). Concentration is a district-level concept."
        ),
    },
    {
        "title": "Use scenario_results for named flood events",
        "content": (
            "When the user asks about scenarios — 'Thames Valley', 'Severn', "
            "'East Coast Surge', 'Yorkshire Calder/Aire', 'South Coast Storm' — "
            "use the gold.scenario_results table. Each row already carries "
            "severity_multiplier and scenario_loss for that event."
        ),
    },
    {
        "title": "Flood zones",
        "content": (
            "flood_zone takes string values '1', '2', '3a', '3b' (NOT integers). "
            "'3a' and '3b' together are the high-risk band ('flood zone 3'). "
            "When the user asks about 'flood zone 3', filter for "
            "flood_zone IN ('3a', '3b')."
        ),
    },
    {
        "title": "Money formatting",
        "content": (
            "All monetary columns (sum_insured, total_exposure, premium, "
            "expected_loss, scenario_loss) are in GBP. Express in £ millions "
            "when totals exceed £10m. Round flood_score to integers."
        ),
    },
    {
        "title": "Geographic key",
        "content": (
            "postcode_district is the geographic key joining all tables. It is "
            "a UK postcode district (e.g. 'SW1', 'M1', 'TW9'). region is the "
            "ITL1-style UK label (London, South East, Midlands, etc.)."
        ),
    },
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--catalog", default=os.environ.get("CATALOG", "lr_serverless_aws_us_catalog"))
    p.add_argument("--bronze",  default=os.environ.get("BRONZE_SCHEMA", "radar_bronze"))
    p.add_argument("--silver",  default=os.environ.get("SILVER_SCHEMA", "radar_silver"))
    p.add_argument("--gold",    default=os.environ.get("GOLD_SCHEMA", "radar_gold"))
    p.add_argument("--warehouse-id", default=os.environ.get("DATABRICKS_WAREHOUSE_ID"),
                   help="SQL warehouse ID (required)")
    p.add_argument("--parent-path", default=os.environ.get("GENIE_PARENT_PATH"),
                   help="Workspace folder path, e.g. /Workspace/Users/you@databricks.com (required)")
    p.add_argument("--profile", default=os.environ.get("DATABRICKS_CONFIG_PROFILE", "DEFAULT"))
    p.add_argument("--space-id", default=None,
                   help="If set, skip creation and add curated content to this existing space")
    return p.parse_args()


def databricks_api(profile: str, method: str, endpoint: str, body: dict | None = None) -> dict:
    """Wrap `databricks api {method} {endpoint}` with JSON body, return parsed JSON."""
    cmd = ["databricks", "--profile", profile, "api", method, endpoint]
    if body is not None:
        # Use a temp file for safety with non-ASCII
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(body, f, ensure_ascii=False)
            tmp = f.name
        cmd += ["--json", f"@{tmp}"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if body is not None:
        os.unlink(tmp)
    if result.returncode != 0:
        raise RuntimeError(f"{method} {endpoint} failed: {result.stderr or result.stdout}")
    if not result.stdout.strip():
        return {}
    return json.loads(result.stdout)


def main():
    args = parse_args()
    if not args.space_id and not args.warehouse_id:
        sys.exit("--warehouse-id is required (or use --space-id to add content to an existing space)")
    if not args.space_id and not args.parent_path:
        sys.exit("--parent-path is required (e.g. /Workspace/Users/you@databricks.com)")

    tables = sorted([
        f"{args.catalog}.{args.gold}.flood_concentration",
        f"{args.catalog}.{args.gold}.scenario_results",
        f"{args.catalog}.{args.gold}.scenario_district_detail",
        f"{args.catalog}.{args.silver}.priced_book_output",
        f"{args.catalog}.{args.bronze}.flood_overlay",
    ])

    description = (
        "Flood Portfolio Q&A — UK home insurance flood concentration analytics "
        "for the radar-databricks demo. All data is synthetic (50K policies "
        "across 154 postcode districts). Use postcode_district as the geographic "
        "key. flood_zone takes values '1', '2', '3a', '3b' (3a/3b = the "
        "high-risk band). Region is the ITL1-style UK label."
    )

    if args.space_id:
        space_id = args.space_id
        print(f"Using existing space {space_id}")
    else:
        print(f"Creating Genie space in {args.parent_path}...")
        body = {
            "title":         "Flood Portfolio Q&A",
            "description":   description,
            "warehouse_id":  args.warehouse_id,
            "parent_path":   args.parent_path,
            "serialized_space": json.dumps({
                "version": 2,
                "data_sources": {
                    "tables": [{"identifier": t} for t in tables],
                },
            }),
        }
        resp = databricks_api(args.profile, "post", "/api/2.0/genie/spaces", body)
        space_id = resp["space_id"]
        print(f"  ✓ space_id: {space_id}")

    # ── Curated sample questions ──────────────────────────────────────────
    print(f"\nAdding {len(SAMPLE_QUESTIONS)} curated sample questions...")
    for q in SAMPLE_QUESTIONS:
        body = {"curated_question": {"question_text": q,
                                     "question_type": "SAMPLE_QUESTION"}}
        databricks_api(args.profile, "post",
                       f"/api/2.0/data-rooms/{space_id}/curated-questions", body)
        print(f"  ✓ {q[:60]}{'...' if len(q) > 60 else ''}")

    # ── General instructions ──────────────────────────────────────────────
    print(f"\nAdding {len(INSTRUCTIONS)} general instructions...")
    for inst in INSTRUCTIONS:
        databricks_api(args.profile, "post",
                       f"/api/2.0/data-rooms/{space_id}/instructions", inst)
        print(f"  ✓ {inst['title']}")

    # ── Done ──────────────────────────────────────────────────────────────
    workspace_host = subprocess.run(
        ["databricks", "--profile", args.profile, "auth", "describe", "-o", "json"],
        capture_output=True, text=True,
    )
    host = ""
    if workspace_host.returncode == 0:
        try:
            host = json.loads(workspace_host.stdout).get("details", {}).get("host", "")
        except Exception:
            pass

    print(f"\nDone.")
    print(f"  space_id:  {space_id}")
    if host:
        print(f"  URL:       {host}/genie/rooms/{space_id}")


if __name__ == "__main__":
    main()
