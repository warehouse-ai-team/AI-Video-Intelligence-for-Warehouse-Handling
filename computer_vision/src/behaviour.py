"""
Phase 6 - Behaviour detection engine.

Reads features.csv (from features.py) and applies rule-based temporal-window
detectors for each behaviour in config/behaviours.yaml. Rules operate on the
SMOOTHED motion signals to avoid single-frame noise triggering false events.

Every detector returns candidate events as dicts:
    {behaviour, start_frame, end_frame, start_time, end_time, confidence, reason}

IMPORTANT LIMITATION (state this, don't hide it): thresholds below are
reasonable pixel-space defaults, NOT calibrated against a labeled dataset
(we have 6 clips of ground truth, not enough for statistical threshold
tuning). Expect to adjust threshold constants after running against
data/annotations/ground_truth.csv - see evaluation.py.
"""

import numpy as np
import pandas as pd
import yaml


def load_behaviour_config(path="config/behaviours.yaml"):
    with open(path) as f:
        return yaml.safe_load(f)


def _merge_overlapping_windows(frame_indices, max_gap_frames=5):
    """Given a sorted list of frame indices where a condition is True, group
    into contiguous windows, tolerating small gaps (missed detections)."""
    if len(frame_indices) == 0:
        return []
    windows = []
    start = frame_indices[0]
    prev = frame_indices[0]
    for f in frame_indices[1:]:
        if f - prev > max_gap_frames:
            windows.append((start, prev))
            start = f
        prev = f
    windows.append((start, prev))
    return windows


def detect_dropping(feat, fps, drop_speed_thresh=250, stop_speed_thresh=60, min_duration_s=0.15):
    """
    Signal: sustained downward vertical velocity (vy_smooth > threshold,
    remember +y = downward in image coords) followed shortly by a sharp
    drop in speed (impact-like stop).
    """
    events = []
    falling = feat["vy_smooth"] > drop_speed_thresh
    fall_frames = feat.loc[falling, "frame"].tolist()
    windows = _merge_overlapping_windows(fall_frames, max_gap_frames=int(fps * 0.2))

    for (start_f, end_f) in windows:
        duration = (end_f - start_f) / fps
        if duration < min_duration_s:
            continue
        # look just after the fall window for a sudden stop
        post = feat[(feat["frame"] > end_f) & (feat["frame"] <= end_f + int(fps * 0.5))]
        stopped = not post.empty and (post["speed_smooth"] < stop_speed_thresh).any()
        confidence = 0.55 + (0.25 if stopped else 0.0)
        events.append({
            "behaviour": "dropping",
            "start_frame": int(start_f), "end_frame": int(end_f),
            "start_time": round(start_f / fps, 2), "end_time": round(end_f / fps, 2),
            "confidence": round(min(confidence, 0.95), 2),
            "reason": f"Sustained downward motion ({duration:.2f}s)"
                      + (" followed by sudden stop" if stopped else ""),
        })
    return events


def detect_throwing(feat, fps, release_speed_thresh=300, min_duration_s=0.15):
    """
    Signal: high overall speed while the product is far from the nearest
    person (i.e. moving on its own, no longer supported/carried).
    """
    events = []
    fast_and_away = (feat["speed_smooth"] > release_speed_thresh) & (feat["nearest_person_dist"] > 80)
    frames = feat.loc[fast_and_away, "frame"].tolist()
    windows = _merge_overlapping_windows(frames, max_gap_frames=int(fps * 0.2))

    for (start_f, end_f) in windows:
        duration = (end_f - start_f) / fps
        if duration < min_duration_s:
            continue
        events.append({
            "behaviour": "throwing",
            "start_frame": int(start_f), "end_frame": int(end_f),
            "start_time": round(start_f / fps, 2), "end_time": round(end_f / fps, 2),
            "confidence": 0.6,
            "reason": f"High-speed product motion while detached from nearest person ({duration:.2f}s)",
        })
    return events


def detect_dragging(feat, fps, floor_y_percentile=70, horiz_speed_thresh=40,
                     proximity_thresh=150, min_duration_s=0.5):
    """
    Signal: product stays in the lower part of the frame (floor proxy) AND
    moves mostly horizontally AND stays close to a person for a sustained
    period (being pulled/pushed rather than lifted/carried normally).
    """
    events = []
    if feat["floor_proxy_y"].dropna().empty:
        return events
    floor_thresh = np.nanpercentile(feat["floor_proxy_y"], floor_y_percentile)

    low_and_moving = (
        (feat["floor_proxy_y"] >= floor_thresh) &
        (feat["vx_smooth"].abs() > horiz_speed_thresh) &
        (feat["nearest_person_dist"] < proximity_thresh)
    )
    frames = feat.loc[low_and_moving, "frame"].tolist()
    windows = _merge_overlapping_windows(frames, max_gap_frames=int(fps * 0.3))

    for (start_f, end_f) in windows:
        duration = (end_f - start_f) / fps
        if duration < min_duration_s:
            continue
        events.append({
            "behaviour": "dragging",
            "start_frame": int(start_f), "end_frame": int(end_f),
            "start_time": round(start_f / fps, 2), "end_time": round(end_f / fps, 2),
            "confidence": 0.55,
            "reason": f"Product stayed low and moved horizontally near a person for {duration:.2f}s",
        })
    return events


def detect_rough_handling(feat, fps, accel_thresh=400, direction_change_thresh=2.0, min_duration_s=0.1):
    """Signal: high acceleration magnitude or sharp direction changes."""
    events = []
    rough = (feat["acceleration_smooth"].abs() > accel_thresh) | (feat["direction_change"] > direction_change_thresh)
    frames = feat.loc[rough, "frame"].tolist()
    windows = _merge_overlapping_windows(frames, max_gap_frames=int(fps * 0.2))

    for (start_f, end_f) in windows:
        duration = (end_f - start_f) / fps
        if duration < min_duration_s:
            continue
        events.append({
            "behaviour": "rough_handling",
            "start_frame": int(start_f), "end_frame": int(end_f),
            "start_time": round(start_f / fps, 2), "end_time": round(end_f / fps, 2),
            "confidence": 0.5,
            "reason": f"High acceleration / sharp direction change over {duration:.2f}s",
        })
    return events


DETECTORS = {
    "dropping": detect_dropping,
    "throwing": detect_throwing,
    "dragging": detect_dragging,
    "rough_handling": detect_rough_handling,
}


def run_behaviour_engine(features_csv, fps, config_path="config/behaviours.yaml"):
    feat = pd.read_csv(features_csv)
    if feat.empty or feat["product_cx"].dropna().empty:
        return []

    config = load_behaviour_config(config_path)
    all_events = []
    for name, fn in DETECTORS.items():
        behaviour_cfg = config["behaviours"].get(name, {})
        min_conf = behaviour_cfg.get("min_confidence", 0.5)
        events = fn(feat, fps)
        for e in events:
            if e["confidence"] >= min_conf:
                e["risk"] = behaviour_cfg.get("risk", "MEDIUM")
                all_events.append(e)

    all_events.sort(key=lambda e: e["start_time"])
    return all_events
