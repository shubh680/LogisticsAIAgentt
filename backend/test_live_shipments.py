"""
Test runner: runs risk_reasoning_agent against every row in live_shipments.csv
and saves results to risk_results.json
"""

import csv
import json
import time
from datetime import datetime, timezone
from risk_reasoning_agent import risk_reasoning_agent

# Map carrier names → reliability score (0–1)
CARRIER_RELIABILITY = {
    "BlueDart":   0.88,
    "Swift":      0.72,
    "Delhivery":  0.76,
}

def parse_eta_hours(planned_arrival_str: str) -> float:
    """Return hours from now until planned arrival (min 0)."""
    planned = datetime.fromisoformat(planned_arrival_str)
    if planned.tzinfo is None:
        planned = planned.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    delta_hours = (planned - now).total_seconds() / 3600
    return round(max(delta_hours, 0), 2)


def build_event(row: dict) -> dict:
    """Map CSV columns → agent input fields."""
    return {
        "shipment_id":        row["shipment_id"],
        "warehouse_load":     round(int(row["warehouse_load_pct"]) / 100, 2),
        "carrier_reliability": CARRIER_RELIABILITY.get(row["carrier"], 0.75),
        "traffic_delay":      float(row["traffic_density"]),
        "eta_hours":          parse_eta_hours(row["planned_arrival"]),
    }


def main():
    csv_path     = "live_shipments.csv"
    output_path  = "risk_results.json"

    results = []

    with open(csv_path, newline="") as f:
        reader = list(csv.DictReader(f))

    total = len(reader)
    print(f"Processing {total} shipments...\n")

    for i, row in enumerate(reader, 1):
        event = build_event(row)
        print(f"[{i}/{total}] {event['shipment_id']} ...", end=" ", flush=True)

        try:
            result = risk_reasoning_agent(event)
            # Attach extra context from CSV for the output report
            result["carrier"]          = row["carrier"]
            result["weather"]          = row["weather"]
            result["current_delay_min"] = int(row["current_delay_minutes"])
            result["is_delayed"]        = row["is_delayed"] == "1"
            result["priority"]          = row["shipment_priority"]
            results.append(result)
            print(f"risk={result['risk_level']} ({result['risk_score']})")
        except Exception as e:
            print(f"ERROR: {e}")
            results.append({"shipment_id": event["shipment_id"], "error": str(e)})

        # Polite rate-limit pause (Groq free tier: 30 req/min)
        time.sleep(2)

    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n✅ Done. Results saved to {output_path}")

    # Summary stats
    levels = [r.get("risk_level") for r in results if "risk_level" in r]
    print(f"\n--- Risk Summary ---")
    for level in ["low", "medium", "high"]:
        print(f"  {level.upper():6s}: {levels.count(level)}")


if __name__ == "__main__":
    main()
