#!/usr/bin/env python3
"""Create / update the 'Flood Concentration View' Lakeview dashboard.

Adapted from the solvency-ii-qrt-demo-pnc dashboard pattern. Parameterised so
it works on any workspace — pass --warehouse-id / --profile / --parent-path
or set the equivalent env vars.

Usage:
  scripts/create_dashboard.py \
    --catalog radar_databricks_demo \
    --gold-schema gold \
    --warehouse-id YOUR_WAREHOUSE_ID \
    --profile DEFAULT \
    --parent-path /Users/your.email@databricks.com

Adding --update DASHBOARD_ID overwrites an existing dashboard rather than
creating a new one.
"""
from __future__ import annotations
import argparse
import json
import os
import subprocess
import sys
import uuid


def uid() -> str:
    return uuid.uuid4().hex[:8]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--catalog",       default=os.environ.get("CATALOG", "radar_databricks_demo"))
    p.add_argument("--gold-schema",   default=os.environ.get("GOLD_SCHEMA", "gold"))
    p.add_argument("--silver-schema", default=os.environ.get("SILVER_SCHEMA", "silver"))
    p.add_argument("--warehouse-id",  default=os.environ.get("DATABRICKS_WAREHOUSE_ID"),
                   help="SQL warehouse ID for dashboard queries (required)")
    p.add_argument("--profile",       default=os.environ.get("DATABRICKS_CONFIG_PROFILE", "DEFAULT"))
    p.add_argument("--parent-path",   default=os.environ.get("DASHBOARD_PARENT_PATH"),
                   help="Workspace folder to create the dashboard in, e.g. /Users/you@databricks.com")
    p.add_argument("--update",        default=None,
                   help="Existing dashboard ID — if set, updates instead of creating")
    return p.parse_args()


def main():
    args = parse_args()
    if not args.warehouse_id:
        sys.exit("--warehouse-id (or DATABRICKS_WAREHOUSE_ID env) is required")
    if not args.update and not args.parent_path:
        sys.exit("--parent-path (or DASHBOARD_PARENT_PATH env) is required when creating new")

    fqn_gold   = f"{args.catalog}.{args.gold_schema}"
    fqn_silver = f"{args.catalog}.{args.silver_schema}"

    # ── Datasets ──────────────────────────────────────────────────────────
    datasets = []

    def ds(name, display, sql):
        oneline = " ".join(line.strip() for line in sql.strip().splitlines())
        datasets.append({"name": name, "displayName": display, "queryLines": [oneline]})
        return name

    ds_kpis = ds("ds_kpis", "Portfolio KPIs",
        f"""SELECT
                COUNT(*)                         AS districts,
                SUM(policy_count)                AS policies,
                ROUND(SUM(total_exposure) / 1e9, 2) AS exposure_bn,
                ROUND(SUM(total_premium)  / 1e6, 1) AS premium_m,
                ROUND(SUM(total_expected_loss) / 1e6, 1) AS expected_loss_m,
                ROUND(SUM(CASE WHEN flood_zone IN ('3a','3b') THEN total_exposure END)
                      / SUM(total_exposure) * 100, 1) AS pct_book_zone3,
                ROUND(SUM(CASE WHEN flood_zone IN ('3a','3b') THEN total_expected_loss END)
                      / SUM(total_expected_loss) * 100, 1) AS pct_loss_zone3
            FROM {fqn_gold}.flood_concentration""")

    ds_map = ds("ds_map", "Concentration Map",
        f"""SELECT
                postcode_district, region, flood_zone, flood_score,
                centroid_lat, centroid_lng, policy_count,
                ROUND(total_exposure / 1e6, 1)      AS exposure_m,
                ROUND(total_expected_loss / 1e3, 1) AS expected_loss_k,
                nearest_watercourse
            FROM {fqn_gold}.flood_concentration""")

    ds_top10 = ds("ds_top10", "Top accumulations",
        f"""SELECT
                postcode_district, region, flood_zone, flood_score,
                policy_count,
                ROUND(total_exposure / 1e6, 1)      AS exposure_m,
                ROUND(max_single_risk / 1e6, 2)     AS max_risk_m,
                ROUND(total_premium / 1e3, 1)       AS premium_k,
                ROUND(total_expected_loss / 1e3, 1) AS expected_loss_k,
                nearest_watercourse
            FROM {fqn_gold}.flood_concentration
            ORDER BY total_exposure DESC
            LIMIT 15""")

    ds_top10_loss = ds("ds_top10_loss", "Top by expected loss",
        f"""SELECT
                postcode_district, region, flood_zone, flood_score,
                policy_count,
                ROUND(total_exposure / 1e6, 1)      AS exposure_m,
                ROUND(total_expected_loss / 1e3, 1) AS expected_loss_k
            FROM {fqn_gold}.flood_concentration
            ORDER BY total_expected_loss DESC
            LIMIT 10""")

    ds_region = ds("ds_region", "Exposure by region",
        f"""SELECT
                region,
                SUM(policy_count) AS policies,
                ROUND(SUM(total_exposure) / 1e6, 0)  AS exposure_m,
                ROUND(SUM(total_premium)  / 1e3, 1)  AS premium_k,
                ROUND(SUM(total_expected_loss) / 1e3, 1) AS expected_loss_k
            FROM {fqn_gold}.flood_concentration
            GROUP BY region
            ORDER BY exposure_m DESC""")

    ds_zone_mix = ds("ds_zone_mix", "Exposure by flood zone",
        f"""SELECT
                flood_zone,
                CASE flood_zone
                    WHEN '1'  THEN '1 — Low'
                    WHEN '2'  THEN '2 — Medium'
                    WHEN '3a' THEN '3a — High'
                    WHEN '3b' THEN '3b — Very High'
                END AS zone_label,
                SUM(policy_count) AS policies,
                ROUND(SUM(total_exposure) / 1e6, 0) AS exposure_m,
                ROUND(SUM(total_expected_loss) / 1e3, 0) AS expected_loss_k
            FROM {fqn_gold}.flood_concentration
            GROUP BY flood_zone
            ORDER BY flood_zone""")

    ds_scenarios = ds("ds_scenarios", "Scenario Stress",
        f"""SELECT
                scenario, severity_multiplier, districts_count, policy_count,
                ROUND(total_exposure / 1e6, 0)    AS exposure_m,
                ROUND(total_premium / 1e6, 2)     AS premium_m,
                ROUND(scenario_loss / 1e6, 2)     AS scenario_loss_m,
                loss_to_premium_pct
            FROM {fqn_gold}.scenario_results
            ORDER BY scenario_loss DESC""")

    # ── Widget builders ──────────────────────────────────────────────────
    def counter_widget(dataset, field, title):
        return {
            "name": uid(),
            "queries": [{"name": "main_query", "query": {
                "datasetName": dataset,
                "fields": [{"name": field, "expression": f"`{field}`"}],
                "disaggregated": True,
            }}],
            "spec": {"version": 2, "widgetType": "counter",
                     "encodings": {"value": {"fieldName": field, "displayName": title}},
                     "frame": {"showTitle": True, "title": title}},
        }

    def map_widget(dataset, lat, lng, size, color, title, label_field=None):
        wid = uid()
        fields = [
            {"name": lat,   "expression": f"`{lat}`"},
            {"name": lng,   "expression": f"`{lng}`"},
            {"name": size,  "expression": f"`{size}`"},
            {"name": color, "expression": f"`{color}`"},
        ]
        if label_field:
            fields.append({"name": label_field, "expression": f"`{label_field}`"})
        enc = {
            "latitude":  {"fieldName": lat,  "scale": {"type": "quantitative"}, "displayName": "lat"},
            "longitude": {"fieldName": lng,  "scale": {"type": "quantitative"}, "displayName": "lng"},
            "size":      {"fieldName": size, "scale": {"type": "quantitative"}, "displayName": size},
            "color":     {"fieldName": color, "scale": {"type": "quantitative",
                                                        "scheme": {"name": "redyellow", "reverse": True}},
                          "displayName": color},
        }
        if label_field:
            enc["label"] = {"fieldName": label_field, "displayName": label_field}
        return {
            "name": wid,
            "queries": [{"name": "main_query", "query": {
                "datasetName": dataset, "fields": fields, "disaggregated": True}}],
            "spec": {"version": 3, "widgetType": "symbol-map", "encodings": enc,
                     "frame": {"showTitle": True, "title": title}},
        }

    def bar_widget(dataset, x, y, title, color=None, sort=None):
        fields = [
            {"name": x, "expression": f"`{x}`"},
            {"name": y, "expression": f"`{y}`"},
        ]
        enc = {
            "x": {"fieldName": x, "scale": {"type": "categorical"}, "displayName": x},
            "y": {"fieldName": y, "scale": {"type": "quantitative"}, "displayName": y},
        }
        if sort:
            enc["x"]["scale"]["sort"] = {"by": sort}
        if color:
            fields.append({"name": color, "expression": f"`{color}`"})
            enc["color"] = {"fieldName": color, "scale": {"type": "categorical"}, "displayName": color}
        return {
            "name": uid(),
            "queries": [{"name": "main_query", "query": {
                "datasetName": dataset, "fields": fields, "disaggregated": True}}],
            "spec": {"version": 3, "widgetType": "bar", "encodings": enc,
                     "frame": {"showTitle": True, "title": title}},
        }

    def table_widget(dataset, columns, title):
        fields = [{"name": c[0], "expression": f"`{c[0]}`"} for c in columns]
        col_specs = []
        for c in columns:
            spec = {"fieldName": c[0], "title": c[1], "type": "string", "displayAs": "string"}
            if len(c) > 2 and c[2] == "number":
                spec["type"] = "float"
                spec["displayAs"] = "number"
                spec["alignContent"] = "right"
                if len(c) > 3:
                    spec["numberFormat"] = c[3]
            col_specs.append(spec)
        return {
            "name": uid(),
            "queries": [{"name": "main_query", "query": {
                "datasetName": dataset, "fields": fields, "disaggregated": True}}],
            "spec": {"version": 1, "widgetType": "table",
                     "encodings": {"columns": col_specs},
                     "frame": {"showTitle": True, "title": title}},
        }

    def md_widget(text):
        return {"name": uid(), "textbox_spec": text}

    def pos(x, y, w, h):
        return {"x": x, "y": y, "width": w, "height": h}

    def lay(widget, position):
        return {"widget": widget, "position": position}

    # ── Layout ────────────────────────────────────────────────────────────
    main_layout = [
        lay(md_widget("# Flood Concentration View\n"
                      "**Radar prices each risk. Databricks shows you what those priced risks add up to.** "
                      "Synthetic UK home insurance portfolio. Geographic distribution weighted to UK "
                      "population centres; flood scores geographically coherent (Thames, Severn, Trent, "
                      "Calder/Aire, East Anglian fens, south-coast surge zones)."),
            pos(0, 0, 6, 1)),

        # KPI tiles
        lay(counter_widget(ds_kpis, "exposure_bn",     "Total Exposure (£bn)"),     pos(0, 1, 1, 2)),
        lay(counter_widget(ds_kpis, "premium_m",       "Gross Written Premium (£m)"),pos(1, 1, 1, 2)),
        lay(counter_widget(ds_kpis, "expected_loss_m", "Expected Loss (£m)"),       pos(2, 1, 1, 2)),
        lay(counter_widget(ds_kpis, "pct_book_zone3",  "% Book in Zone 3 (a/b)"),   pos(3, 1, 1, 2)),
        lay(counter_widget(ds_kpis, "pct_loss_zone3",  "% Loss in Zone 3 (a/b)"),   pos(4, 1, 1, 2)),
        lay(counter_widget(ds_kpis, "policies",        "Policy Count"),             pos(5, 1, 1, 2)),

        # Map — the centrepiece
        lay(map_widget(ds_map,
                       lat="centroid_lat", lng="centroid_lng",
                       size="exposure_m", color="flood_score",
                       title="UK Concentration Map — bubble = exposure (£m), colour = flood score (0–100)",
                       label_field="postcode_district"),
            pos(0, 3, 6, 8)),

        # Top-10 accumulation table
        lay(table_widget(ds_top10,
                         [("postcode_district", "District"),
                          ("region",            "Region"),
                          ("flood_zone",        "Zone"),
                          ("flood_score",       "Score", "number", "0"),
                          ("policy_count",      "Policies", "number", "#,##0"),
                          ("exposure_m",        "Exposure (£m)", "number", "#,##0.0"),
                          ("max_risk_m",        "Max Risk (£m)", "number", "#,##0.00"),
                          ("expected_loss_k",   "Expected Loss (£k)", "number", "#,##0.0"),
                          ("nearest_watercourse","Watercourse")],
                         "Top 15 Districts by Exposure"),
            pos(0, 11, 6, 5)),

        # Region + zone splits
        lay(bar_widget(ds_region, "region", "exposure_m",
                       "Exposure by Region (£m)", sort="y-reversed"),
            pos(0, 16, 3, 4)),
        lay(bar_widget(ds_zone_mix, "zone_label", "exposure_m",
                       "Exposure by Flood Zone (£m)"),
            pos(3, 16, 3, 4)),

        # Scenario stress
        lay(md_widget("## Scenario Stress\n"
                      "Pre-computed loss under named flood scenarios. Each row applies a severity "
                      "multiplier to the priced expected_loss for the affected districts."),
            pos(0, 20, 6, 1)),

        lay(table_widget(ds_scenarios,
                         [("scenario",            "Scenario"),
                          ("severity_multiplier", "Severity ×", "number", "0.0"),
                          ("districts_count",     "Districts", "number", "0"),
                          ("policy_count",        "Policies", "number", "#,##0"),
                          ("exposure_m",          "Exposure (£m)", "number", "#,##0"),
                          ("premium_m",           "Premium (£m)", "number", "#,##0.00"),
                          ("scenario_loss_m",     "Scenario Loss (£m)", "number", "#,##0.00"),
                          ("loss_to_premium_pct", "Loss/Premium %", "number", "0.0")],
                         "Named Flood Scenarios"),
            pos(0, 21, 6, 4)),

        lay(bar_widget(ds_scenarios, "scenario", "scenario_loss_m",
                       "Scenario Loss (£m) — sized by severity × affected exposure", sort="y-reversed"),
            pos(0, 25, 6, 4)),
    ]

    serialized = {
        "datasets": datasets,
        "pages": [{
            "name": uid(),
            "displayName": "Flood Concentration",
            "pageType": "PAGE_TYPE_CANVAS",
            "layout": main_layout,
        }],
        "uiSettings": {
            "theme": {"widgetHeaderAlignment": "ALIGNMENT_UNSPECIFIED"},
            "applyModeEnabled": False,
        },
    }

    serialized_json = json.dumps(serialized)

    if args.update:
        print(f"Updating dashboard {args.update}...")
        result = subprocess.run(
            ["databricks", "api", "patch", f"/api/2.0/lakeview/dashboards/{args.update}",
             "--profile", args.profile,
             "--json", json.dumps({"serialized_dashboard": serialized_json})],
            capture_output=True, text=True,
        )
    else:
        print(f"Creating dashboard in {args.parent_path}...")
        result = subprocess.run(
            ["databricks", "api", "post", "/api/2.0/lakeview/dashboards",
             "--profile", args.profile,
             "--json", json.dumps({
                "display_name": "Flood Concentration View",
                "warehouse_id": args.warehouse_id,
                "parent_path":  args.parent_path,
                "serialized_dashboard": serialized_json,
            })],
            capture_output=True, text=True,
        )

    if result.returncode != 0:
        sys.exit(f"Error: {result.stderr}\n{result.stdout}")

    resp = json.loads(result.stdout)
    dashboard_id = resp.get("dashboard_id", args.update)
    print(f"Dashboard ID: {dashboard_id}")

    # Publish
    print("Publishing...")
    pub = subprocess.run(
        ["databricks", "api", "post",
         f"/api/2.0/lakeview/dashboards/{dashboard_id}/published",
         "--profile", args.profile,
         "--json", json.dumps({"warehouse_id": args.warehouse_id, "embed_credentials": True})],
        capture_output=True, text=True,
    )
    if pub.returncode != 0:
        print(f"  [warn] publish: {pub.stderr}")

    print(f"\nDone. Dashboard ID: {dashboard_id}")
    print(f"  → /dashboardsv3/{dashboard_id}  (open in your workspace)")


if __name__ == "__main__":
    main()
