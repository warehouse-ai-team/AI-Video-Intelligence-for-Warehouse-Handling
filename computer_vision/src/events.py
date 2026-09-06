"""
Phase 7 - Event generation. Converts behaviour-engine events into the
stable JSON/CSV schema other team members (dashboard/LLM/analytics) consume.
"""

import json
import csv
import os


def build_event_records(events, video_id, evidence_dir="outputs/clips"):
    records = []
    for i, e in enumerate(events, start=1):
        event_id = f"EVT_{video_id}_{i:03d}"
        records.append({
            "event_id": event_id,
            "video_id": video_id,
            "start_time": e["start_time"],
            "end_time": e["end_time"],
            "behaviour": e["behaviour"],
            "risk_level": e["risk"],
            "confidence": e["confidence"],
            "evidence": os.path.join(evidence_dir, f"{event_id}.mp4"),
            "reason": e["reason"],
            # Explicit distinction per brief section 16 - never claim confirmed damage
            "damage_status": "potential_damage_risk",
        })
    return records


def write_events(records, json_path, csv_path):
    os.makedirs(os.path.dirname(json_path), exist_ok=True)
    with open(json_path, "w") as f:
        json.dump(records, f, indent=2)

    if records:
        fieldnames = list(records[0].keys())
    else:
        fieldnames = ["event_id", "video_id", "start_time", "end_time", "behaviour",
                      "risk_level", "confidence", "evidence", "reason", "damage_status"]
    with open(csv_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(records)
