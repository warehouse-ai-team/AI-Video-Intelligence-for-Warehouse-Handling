"""
Phase 6 - Behaviour detection engine. (Member 2 - Behaviour Intelligence)

Reads features.csv (from features.py) + tracking.csv (for multi-product /
keypoint signals that features.py's single-"primary product" simplification
doesn't carry) and applies rule-based temporal-window detectors for all 10
behaviours in config/behaviours.yaml.

Every detector returns candidate events as dicts:
    {behaviour, start_frame, end_frame, start_time, end_time, confidence, reason}

STATUS as of this pass:
- dropping / throwing / dragging / rough_handling: existing 4 rules,
  tightened (see per-function docstrings) to cut known false-positive modes.
- improper_stacking / unstable_stacking / strap_assisted_handling /
  stepping_on_carton: newly implemented.
- outside_designated_area: implemented but INACTIVE until roi_zones in
  behaviours.yaml are filled in with real per-camera coordinates.
- unsafe_loading_sequence: implemented as a META-rule over the other 9
  detectors' combined output (temporal chaining), not over raw features.

IMPORTANT LIMITATION (state this, don't hide it): every threshold in
config/behaviours.yaml is a physics-reasoning + synthetic-fixture-tested
default, NOT calibrated against real footage yet, because the product
detector currently feeding the pipeline is the unreliable blob detector
(see data/annotations/detection_findings.md). Re-tune via
src/evaluation.py once Member 1 validates YOLO-World and the real 6-video
tracking.csv files are regenerated. See tests/test_behaviour_synthetic.py
for what IS verified right now: that each rule fires on the traffic pattern
it's designed for, in isolation.
"""

import os
from collections import defaultdict

import numpy as np
import pandas as pd
import yaml

try:
    from features import load_all_product_boxes, load_person_ankle_points
except ImportError:  # pragma: no cover - allows running from a different cwd
    from .features import load_all_product_boxes, load_person_ankle_points


def load_behaviour_config(path="config/behaviours.yaml"):
    with open(path) as f:
        return yaml.safe_load(f)


def _merge_overlapping_windows(frame_indices, max_gap_frames=5):
    """Given a sorted list of frame indices where a condition is True, group
    into contiguous windows, tolerating small gaps (missed detections)."""
    if len(frame_indices) == 0:
        return []
    frame_indices = sorted(frame_indices)
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


def _time_iou(a, b):
    """Temporal IoU between two events' [start_time, end_time] intervals."""
    inter = max(0.0, min(a["end_time"], b["end_time"]) - max(a["start_time"], b["start_time"]))
    union = max(a["end_time"], b["end_time"]) - min(a["start_time"], b["start_time"])
    return inter / union if union > 0 else 0.0


# ---------------------------------------------------------------------------
# Existing 4 rules - tightened versions
# ---------------------------------------------------------------------------

def detect_dropping(feat, fps, t):
    """
    Signal: sustained downward vertical velocity followed shortly by a sharp
    drop in speed (impact-like stop).

    TIGHTENED (vs. original): now also requires a minimum NET vertical
    displacement across the window (min_net_vertical_drop_px), not just an
    instantaneous velocity spike - a single noisy frame with vy_smooth over
    threshold used to be enough to open a window; that let 1-2 frame jitter
    masquerade as a fall. Real drops displace the product a meaningful
    number of pixels; jitter mostly doesn't.
    """
    events = []
    falling = feat["vy_smooth"] > t.get("drop_speed_thresh", 250)
    fall_frames = feat.loc[falling, "frame"].tolist()
    windows = _merge_overlapping_windows(fall_frames, max_gap_frames=int(fps * 0.2))
    cy_by_frame = dict(zip(feat["frame"], feat["product_cy"]))

    for (start_f, end_f) in windows:
        duration = (end_f - start_f + 1) / fps  # +1: inclusive frame count, so a single-frame window has real duration
        if duration < t.get("min_duration_s", 0.15):
            continue
        net_drop = cy_by_frame.get(end_f, np.nan) - cy_by_frame.get(start_f, np.nan)
        if pd.isna(net_drop) or net_drop < t.get("min_net_vertical_drop_px", 40):
            continue
        post = feat[(feat["frame"] > end_f) & (feat["frame"] <= end_f + int(fps * 0.5))]
        stopped = not post.empty and (post["speed_smooth"] < t.get("stop_speed_thresh", 60)).any()
        confidence = 0.55 + (0.25 if stopped else 0.0)
        events.append({
            "behaviour": "dropping",
            "start_frame": int(start_f), "end_frame": int(end_f),
            "start_time": round(start_f / fps, 2), "end_time": round(end_f / fps, 2),
            "confidence": round(min(confidence, 0.95), 2),
            "reason": f"Sustained downward motion ({duration:.2f}s, net {net_drop:.0f}px)"
                      + (" followed by sudden stop" if stopped else ""),
        })
    return events


def detect_throwing(feat, fps, t):
    """
    Signal: high overall speed while the product is far from the nearest
    person AND that speed is mostly horizontal (an outward throw), not a
    straight vertical fall.

    TIGHTENED (vs. original): two new guards address the false-positive
    mode documented in detection_findings.md ("blob detector fires
    'throwing' almost continuously on busy scenes"):
      1. horiz_component_min_frac - a window is only "throwing" if a
         meaningful share of the motion is horizontal. Vertical-only
         high-speed motion away from a person is more likely a drop or a
         tracker jump than a throw.
      2. min_continuous_frames - requires the window to span several
         consecutive frames, not a single-frame spike (which is usually a
         track-ID jump/re-detection artifact, not real motion).
    """
    events = []
    fast_and_away = (
        (feat["speed_smooth"] > t.get("release_speed_thresh", 300)) &
        (feat["nearest_person_dist"] > t.get("person_distance_thresh", 80))
    )
    frames = feat.loc[fast_and_away, "frame"].tolist()
    windows = _merge_overlapping_windows(frames, max_gap_frames=int(fps * 0.2))

    for (start_f, end_f) in windows:
        duration = (end_f - start_f + 1) / fps  # +1: inclusive frame count, so a single-frame window has real duration
        if duration < t.get("min_duration_s", 0.15):
            continue
        if (end_f - start_f + 1) < t.get("min_continuous_frames", 3):
            continue
        sub = feat[(feat["frame"] >= start_f) & (feat["frame"] <= end_f)]
        avg_speed = sub["speed_smooth"].mean()
        avg_horiz = sub["vx_smooth"].abs().mean()
        if not avg_speed or (avg_horiz / avg_speed) < t.get("horiz_component_min_frac", 0.35):
            continue
        events.append({
            "behaviour": "throwing",
            "start_frame": int(start_f), "end_frame": int(end_f),
            "start_time": round(start_f / fps, 2), "end_time": round(end_f / fps, 2),
            "confidence": 0.6,
            "reason": f"High-speed, mostly-horizontal product motion while detached from nearest person ({duration:.2f}s)",
        })
    return events


def detect_dragging(feat, fps, t):
    """Signal: product stays low in frame AND moves horizontally AND stays
    close to a person for a sustained period (pulled/pushed, not lifted)."""
    events = []
    if feat["floor_proxy_y"].dropna().empty:
        return events
    floor_thresh = np.nanpercentile(feat["floor_proxy_y"], t.get("floor_y_percentile", 70))

    low_and_moving = (
        (feat["floor_proxy_y"] >= floor_thresh) &
        (feat["vx_smooth"].abs() > t.get("horiz_speed_thresh", 40)) &
        (feat["nearest_person_dist"] < t.get("proximity_thresh", 150))
    )
    frames = feat.loc[low_and_moving, "frame"].tolist()
    windows = _merge_overlapping_windows(frames, max_gap_frames=int(fps * 0.3))

    for (start_f, end_f) in windows:
        duration = (end_f - start_f + 1) / fps  # +1: inclusive frame count, so a single-frame window has real duration
        if duration < t.get("min_duration_s", 0.5):
            continue
        events.append({
            "behaviour": "dragging",
            "start_frame": int(start_f), "end_frame": int(end_f),
            "start_time": round(start_f / fps, 2), "end_time": round(end_f / fps, 2),
            "confidence": 0.55,
            "reason": f"Product stayed low and moved horizontally near a person for {duration:.2f}s",
        })
    return events


def detect_rough_handling(feat, fps, t):
    """
    Signal: high acceleration magnitude or sharp direction changes.

    TIGHTENED (vs. original): acceleration is now normalized by
    sqrt(product_area) before thresholding (acceleration_normalized, from
    features.py) instead of raw pixel acceleration. A mattress and a small
    box produce very different raw pixel accelerations for the same real
    jolt purely because of their size in frame - normalizing makes one
    threshold meaningful across object sizes instead of biased toward
    flagging large objects.
    """
    events = []
    if "acceleration_normalized" in feat.columns:
        accel = feat["acceleration_normalized"]
    else:  # older features.csv without the normalized column - fall back
        area = (feat["product_w"] * feat["product_h"]).clip(lower=1)
        accel = feat["acceleration_smooth"] / np.sqrt(area)

    rough = (accel.abs() > t.get("accel_thresh_normalized", 55)) | \
            (feat["direction_change"] > t.get("direction_change_thresh", 2.0))
    frames = feat.loc[rough, "frame"].tolist()
    windows = _merge_overlapping_windows(frames, max_gap_frames=int(fps * 0.2))

    for (start_f, end_f) in windows:
        duration = (end_f - start_f + 1) / fps  # +1: inclusive frame count, so a single-frame window has real duration
        if duration < t.get("min_duration_s", 0.1):
            continue
        events.append({
            "behaviour": "rough_handling",
            "start_frame": int(start_f), "end_frame": int(end_f),
            "start_time": round(start_f / fps, 2), "end_time": round(end_f / fps, 2),
            "confidence": 0.5,
            "reason": f"High (size-normalized) acceleration / sharp direction change over {duration:.2f}s",
        })
    return events


MOTION_DETECTORS = {
    "dropping": detect_dropping,
    "throwing": detect_throwing,
    "dragging": detect_dragging,
    "rough_handling": detect_rough_handling,
}


# ---------------------------------------------------------------------------
# New: multi-product stacking rules (need >=2 concurrent product boxes,
# which features.py's single-"primary product" series doesn't carry)
# ---------------------------------------------------------------------------

def _find_stack_pairs(boxes, min_overlap_frac=0.4, max_gap_px=60):
    """
    Returns [(upper_box, lower_box, horiz_overlap_frac), ...] for every pair
    of product boxes in one frame that plausibly form a vertical stack:
    horizontally overlapping enough AND vertically close enough that one
    sits (roughly) on top of the other. "Upper" = smaller cy (higher on
    screen). Pixel-space heuristic, not a real 3D stack reconstruction.
    """
    pairs = []
    for a in boxes:
        for b in boxes:
            if a is b or a["cy"] >= b["cy"]:
                continue  # a must be the visually-upper box
            ox1, ox2 = max(a["x1"], b["x1"]), min(a["x2"], b["x2"])
            overlap = max(0.0, ox2 - ox1)
            min_w = min(a["w"], b["w"])
            if min_w <= 0:
                continue
            overlap_frac = overlap / min_w
            if overlap_frac < min_overlap_frac:
                continue
            vertical_gap = b["y1"] - a["y2"]  # ~0 or negative if touching/overlapping
            if vertical_gap > max_gap_px:
                continue  # too far apart vertically to be a stack, not just side-by-side items
            pairs.append((a, b, overlap_frac))
    return pairs


def detect_improper_stacking(product_boxes_by_frame, fps, t):
    """Signal: a visually larger/heavier-looking item sustained on top of a
    smaller one. Visual-size proxy only - NOT weight-verified."""
    flagged = defaultdict(list)
    for frame, boxes in product_boxes_by_frame.items():
        if len(boxes) < 2:
            continue
        for (upper, lower, _overlap) in _find_stack_pairs(boxes, t.get("min_horizontal_overlap_frac", 0.4)):
            area_ratio = upper["area"] / max(lower["area"], 1)
            if area_ratio > t.get("area_ratio_thresh", 1.15):
                flagged[(upper["track_id"], lower["track_id"])].append(frame)

    events = []
    for (upper_id, lower_id), frames in flagged.items():
        for (start_f, end_f) in _merge_overlapping_windows(frames, max_gap_frames=int(fps * 0.5)):
            duration = (end_f - start_f + 1) / fps  # +1: inclusive frame count, so a single-frame window has real duration
            if duration < t.get("min_duration_s", 1.0):
                continue
            events.append({
                "behaviour": "improper_stacking",
                "start_frame": int(start_f), "end_frame": int(end_f),
                "start_time": round(start_f / fps, 2), "end_time": round(end_f / fps, 2),
                "confidence": 0.55,
                "reason": f"Larger item sustained on top of a smaller item for {duration:.2f}s "
                          f"(product tracks {upper_id}/{lower_id})",
            })
    return events


def detect_unstable_stacking(product_boxes_by_frame, fps, t):
    """Signal: stacked pair with large horizontal centroid offset (leaning/
    overhanging) relative to the lower item's width."""
    flagged = defaultdict(list)
    for frame, boxes in product_boxes_by_frame.items():
        if len(boxes) < 2:
            continue
        for (upper, lower, _overlap) in _find_stack_pairs(boxes, t.get("min_horizontal_overlap_frac", 0.4)):
            lower_w = max(lower["w"], 1)
            offset_frac = abs(upper["cx"] - lower["cx"]) / lower_w
            if offset_frac > t.get("overhang_frac_thresh", 0.35):
                flagged[(upper["track_id"], lower["track_id"])].append(frame)

    events = []
    for (upper_id, lower_id), frames in flagged.items():
        for (start_f, end_f) in _merge_overlapping_windows(frames, max_gap_frames=int(fps * 0.3)):
            duration = (end_f - start_f + 1) / fps  # +1: inclusive frame count, so a single-frame window has real duration
            if duration < t.get("min_duration_s", 0.5):
                continue
            events.append({
                "behaviour": "unstable_stacking",
                "start_frame": int(start_f), "end_frame": int(end_f),
                "start_time": round(start_f / fps, 2), "end_time": round(end_f / fps, 2),
                "confidence": 0.55,
                "reason": f"Stacked item leaning/overhanging relative to its base for {duration:.2f}s "
                          f"(product tracks {upper_id}/{lower_id})",
            })
    return events


# ---------------------------------------------------------------------------
# New: outside_designated_area (inactive until roi_zones are configured)
# ---------------------------------------------------------------------------

def detect_outside_designated_area(feat, fps, allowed_zone, t):
    """
    allowed_zone: (x1, y1, x2, y2) pixel rect the product should stay
    inside, or None if not configured for this video. Returns [] (not an
    error) when None - this is a real, current data-dependency gap, not a
    bug: see behaviours.yaml roi_zones note.
    """
    if not allowed_zone:
        return []
    x1, y1, x2, y2 = allowed_zone
    cx, cy = feat["product_cx"], feat["product_cy"]
    inside = (cx >= x1) & (cx <= x2) & (cy >= y1) & (cy <= y2)
    outside = (~inside) & cx.notna()
    frames = feat.loc[outside, "frame"].tolist()
    windows = _merge_overlapping_windows(frames, max_gap_frames=int(fps * 0.3))

    events = []
    for (start_f, end_f) in windows:
        duration = (end_f - start_f + 1) / fps  # +1: inclusive frame count, so a single-frame window has real duration
        if duration < t.get("min_duration_s", 0.5):
            continue
        events.append({
            "behaviour": "outside_designated_area",
            "start_frame": int(start_f), "end_frame": int(end_f),
            "start_time": round(start_f / fps, 2), "end_time": round(end_f / fps, 2),
            "confidence": 0.65,
            "reason": f"Product centroid left the configured zone for {duration:.2f}s",
        })
    return events


# ---------------------------------------------------------------------------
# New: strap_assisted_handling (low-confidence proxy - documented as such)
# ---------------------------------------------------------------------------

def detect_strap_assisted_handling(feat, fps, t):
    """
    Signal (proxy, not a real strap detector - CCTV resolution can't
    reliably resolve a strap): product moves at moderate, sustained speed
    while staying a roughly CONSTANT (low-variance) distance from the
    nearest person - close enough to be "attached", far enough that it
    isn't a direct hand grip. A person carrying with a strap keeps the
    product at arm's length + strap length fairly consistently; direct
    carrying/dragging tends to vary that distance more as grip shifts.
    """
    t_speed_min, t_speed_max = t.get("speed_min", 15), t.get("speed_max", 220)
    t_gap_min, t_gap_max = t.get("min_gap_px", 15), t.get("max_gap_px", 180)

    speed_ok = feat["speed_smooth"].between(t_speed_min, t_speed_max)
    dist_ok = feat["nearest_person_dist"].between(t_gap_min, t_gap_max)
    candidate = speed_ok & dist_ok
    frames = feat.loc[candidate, "frame"].tolist()
    windows = _merge_overlapping_windows(frames, max_gap_frames=int(fps * 0.3))
    dist_by_frame = dict(zip(feat["frame"], feat["nearest_person_dist"]))

    events = []
    for (start_f, end_f) in windows:
        duration = (end_f - start_f + 1) / fps  # +1: inclusive frame count, so a single-frame window has real duration
        if duration < t.get("min_duration_s", 0.6):
            continue
        window_dists = [dist_by_frame[f] for f in range(start_f, end_f + 1)
                         if f in dist_by_frame and pd.notna(dist_by_frame[f])]
        if len(window_dists) < 2:
            continue
        if float(np.std(window_dists)) > t.get("distance_variation_max", 40):
            continue  # too variable to look like a taut, sustained strap pull
        events.append({
            "behaviour": "strap_assisted_handling",
            "start_frame": int(start_f), "end_frame": int(end_f),
            "start_time": round(start_f / fps, 2), "end_time": round(end_f / fps, 2),
            "confidence": 0.4,  # deliberately low - this is a weak proxy, see docstring
            "reason": f"Sustained moderate, low-variance distance from nearest person for {duration:.2f}s "
                      f"(proxy for strap-assisted vs. direct-grip handling)",
        })
    return events


# ---------------------------------------------------------------------------
# New: stepping_on_carton (needs ankle keypoints - see run_tracking_demo.py)
# ---------------------------------------------------------------------------

def detect_stepping_on_carton(product_boxes_by_frame, ankle_points_by_frame, fps, t):
    if not ankle_points_by_frame:
        return []  # tracking.csv predates ankle-keypoint columns - not an error, just unavailable yet

    flagged_frames = []
    for frame, pts in ankle_points_by_frame.items():
        boxes = product_boxes_by_frame.get(frame, [])
        if not boxes:
            continue
        for (ax, ay) in pts:
            for b in boxes:
                if b["x1"] <= ax <= b["x2"] and b["y1"] <= ay <= b["y2"]:
                    flagged_frames.append(frame)
                    break

    windows = _merge_overlapping_windows(sorted(set(flagged_frames)), max_gap_frames=int(fps * 0.3))
    events = []
    for (start_f, end_f) in windows:
        duration = (end_f - start_f + 1) / fps  # +1: inclusive frame count, so a single-frame window has real duration
        if duration < t.get("min_duration_s", 0.4):
            continue
        events.append({
            "behaviour": "stepping_on_carton",
            "start_frame": int(start_f), "end_frame": int(end_f),
            "start_time": round(start_f / fps, 2), "end_time": round(end_f / fps, 2),
            "confidence": 0.6,
            "reason": f"Foot/ankle keypoint overlapped a carton bounding box for {duration:.2f}s",
        })
    return events


# ---------------------------------------------------------------------------
# New: unsafe_loading_sequence - meta-rule, chains OTHER events together
# ---------------------------------------------------------------------------

def detect_unsafe_loading_sequence(all_events, config, t):
    """
    Signal: an "instability/setup" event (e.g. improper_stacking,
    unstable_stacking, dragging - see behaviours.yaml
    chain_instability_behaviours) followed within chain_window_s by a
    "failure" event (dropping, rough_handling - chain_failure_behaviours).
    Runs AFTER every other detector, over their combined output - this is
    the one rule that reasons about event SEQUENCES rather than raw motion.
    """
    instability_types = set(config.get("chain_instability_behaviours", []))
    failure_types = set(config.get("chain_failure_behaviours", []))
    window_s = t.get("chain_window_s", 8.0)

    instability_events = [e for e in all_events if e["behaviour"] in instability_types]
    failure_events = sorted([e for e in all_events if e["behaviour"] in failure_types],
                             key=lambda e: e["start_time"])

    events = []
    used_failure_idx = set()
    for ie in sorted(instability_events, key=lambda e: e["start_time"]):
        for idx, fe in enumerate(failure_events):
            if idx in used_failure_idx:
                continue
            gap = fe["start_time"] - ie["end_time"]
            if 0 <= gap <= window_s:
                events.append({
                    "behaviour": "unsafe_loading_sequence",
                    "start_frame": ie.get("start_frame"), "end_frame": fe.get("end_frame"),
                    "start_time": ie["start_time"], "end_time": fe["end_time"],
                    "confidence": round(min(ie["confidence"], fe["confidence"]) * 0.9, 2),
                    "reason": f"'{ie['behaviour']}' at {ie['start_time']:.2f}s followed by "
                              f"'{fe['behaviour']}' at {fe['start_time']:.2f}s within {gap:.2f}s "
                              f"- placement/instability leading to failure",
                })
                used_failure_idx.add(idx)
                break
    return events


# ---------------------------------------------------------------------------
# Cross-behaviour suppression (avoid double-counting the same physical event)
# ---------------------------------------------------------------------------

_SUPPRESS_PAIRS = {frozenset(("dropping", "rough_handling"))}


def _suppress_redundant(events, iou_thresh=0.5):
    """If two events of a known-overlapping pair (e.g. dropping vs
    rough_handling - a hard drop often trips both) cover mostly the same
    time window, keep only the higher-confidence one."""
    to_drop = set()
    for i in range(len(events)):
        for j in range(i + 1, len(events)):
            a, b = events[i], events[j]
            if frozenset((a["behaviour"], b["behaviour"])) not in _SUPPRESS_PAIRS:
                continue
            if _time_iou(a, b) >= iou_thresh:
                to_drop.add(j if a["confidence"] >= b["confidence"] else i)
    return [e for idx, e in enumerate(events) if idx not in to_drop]


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def run_behaviour_engine(features_csv, tracking_csv, fps, video_name=None,
                          config_path="config/behaviours.yaml"):
    """
    features_csv: output of features.py (single-primary-product motion series)
    tracking_csv: the raw per-frame tracking CSV (needed for multi-product
                  stacking rules and ankle-keypoint-based stepping_on_carton)
    video_name: key to look up this video's roi_zones entry in the config
                (matches the video_name keys used in content_roi.yaml).
                None / not found -> outside_designated_area returns [].
    """
    feat = pd.read_csv(features_csv)
    config = load_behaviour_config(config_path)

    all_events = []

    if not feat.empty and not feat["product_cx"].dropna().empty:
        for name, fn in MOTION_DETECTORS.items():
            cfg = config["behaviours"].get(name, {})
            for e in fn(feat, fps, cfg.get("thresholds", {})):
                all_events.append(e)

        allowed_zone = None
        zone_cfg = (config.get("roi_zones") or {}).get("loading_zone") or {}
        if video_name and isinstance(zone_cfg, dict) and video_name in zone_cfg:
            allowed_zone = tuple(zone_cfg[video_name])
        cfg = config["behaviours"].get("outside_designated_area", {})
        for e in detect_outside_designated_area(feat, fps, allowed_zone, cfg.get("thresholds", {})):
            all_events.append(e)

        cfg = config["behaviours"].get("strap_assisted_handling", {})
        for e in detect_strap_assisted_handling(feat, fps, cfg.get("thresholds", {})):
            all_events.append(e)

    if os.path.exists(tracking_csv):
        product_boxes_by_frame = load_all_product_boxes(tracking_csv)
        ankle_points_by_frame = load_person_ankle_points(tracking_csv)

        cfg = config["behaviours"].get("improper_stacking", {})
        all_events += detect_improper_stacking(product_boxes_by_frame, fps, cfg.get("thresholds", {}))

        cfg = config["behaviours"].get("unstable_stacking", {})
        all_events += detect_unstable_stacking(product_boxes_by_frame, fps, cfg.get("thresholds", {}))

        cfg = config["behaviours"].get("stepping_on_carton", {})
        all_events += detect_stepping_on_carton(product_boxes_by_frame, ankle_points_by_frame, fps,
                                                 cfg.get("thresholds", {}))

    # Chain rule runs over everything detected so far
    cfg = config["behaviours"].get("unsafe_loading_sequence", {})
    all_events += detect_unsafe_loading_sequence(all_events, config, cfg.get("thresholds", {}))

    all_events = _suppress_redundant(all_events)

    # Apply per-behaviour min_confidence + attach risk level
    final_events = []
    for e in all_events:
        behaviour_cfg = config["behaviours"].get(e["behaviour"], {})
        min_conf = behaviour_cfg.get("min_confidence", 0.5)
        if e["confidence"] >= min_conf:
            e["risk"] = behaviour_cfg.get("risk", "MEDIUM")
            final_events.append(e)

    final_events.sort(key=lambda e: e["start_time"])
    return final_events
