"""
Run the behaviour engine on all 6 videos' real feature CSVs and generate
the final events.json / events.csv.

Usage (from computer_vision folder):
    python generate_all_events.py
"""

import sys
import os
sys.path.insert(0, "src")

from behaviour import run_behaviour_engine
from events import build_event_records, write_events

VIDEOS = {
    "Dock_level__dragging_cupboard": "V001",
    "KD_packets_dragged__heavy_box_kept_on_other_packets": "V002",
    "Rolling_and_dragging_on_wet_floor": "V003",
    "Rolling_and_dropping_carton": "V004",
    "Stepping_on_cartons__vertical_product_kept_horizontally__heavy_product_kept_on_top": "V005",
    "Throwing_Mattresses": "V006",
}

all_records = []
for name, video_id in VIDEOS.items():
    feat_path = f"outputs/tracking/{name}_features.csv"
    if not os.path.exists(feat_path):
        print(f"SKIPPING {video_id} ({name}) - features file not found: {feat_path}")
        continue

    events = run_behaviour_engine(feat_path, fps=30)
    records = build_event_records(events, video_id)
    all_records.extend(records)

    print(f"\n{video_id} ({name}): {len(events)} events")
    for e in events:
        print(f"    {e['start_time']:6.2f}-{e['end_time']:6.2f}s  {e['behaviour']:15s} "
              f"risk={e['risk']:8s} conf={e['confidence']:.2f}")

os.makedirs("outputs/events", exist_ok=True)
write_events(all_records, "outputs/events/events.json", "outputs/events/events.csv")
print(f"\n\nTOTAL: {len(all_records)} events across all 6 videos")
print("Written to outputs/events/events.json and outputs/events/events.csv")
