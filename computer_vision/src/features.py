"""
Phase 5 - Motion feature extraction.

Reads tracking.csv (frame, timestamp, object_id, class, x, y, w, h, cx, cy, confidence)
and produces features.csv with per-frame motion features.

DESIGN DECISION (documented, not hidden): the ProductBlobDetector/SimpleIOUTracker
combo still has real ID churn on this footage (verified: 15-68 unique IDs per
6-50s clip that should have 1-3 real objects). Rather than pretend the IDs are
stable, behaviour detection here treats the LARGEST product blob in each frame
as a single "primary product" position time series, regardless of which
track_id produced it. This is a deliberate hackathon-appropriate shortcut: it
works because every reviewed clip has one dominant product event at a time
(confirmed during Phase 1 video audit). It would NOT work correctly on
footage with multiple simultaneous independent product movements - documented
as a known limitation, not silently assumed away.

For PERSON features we keep this data track_id-based (distance to nearest
person, etc.), and drop that constraint if evaluation later shows people's
IDs are stable enough per-clip to justify it.
"""

import argparse
import pandas as pd
import numpy as np


def extract_features(tracking_csv, fps, smoothing_window=5):
    df = pd.read_csv(tracking_csv)
    if df.empty:
        return pd.DataFrame()

    max_frame = int(df["frame"].max())
    frames = np.arange(0, max_frame + 1)

    # --- Primary product proxy: continuity-constrained, not just "largest blob" ---
    prod = df[df["class"] == "product"].copy()
    prod["area"] = prod["w"] * prod["h"]
    # Picking the largest blob independently each frame lets the trajectory
    # jump between unrelated blobs (blob detector noise/ID churn), which
    # then looks like impossible high-speed motion to the behaviour engine.
    # Verified empirically: this caused 5 spurious "throwing" events on a
    # clip whose only real event was a single "dropping". Fix: prefer the
    # blob nearest to the previous frame's position (if within max_jump_px),
    # falling back to the largest blob when there is no previous position
    # or nothing is within range (e.g. right after a real occlusion/gap).
    max_jump_px = 120  # ~ plausible product displacement in 1/30s at this camera distance
    prod_by_frame = {f: g for f, g in prod.groupby("frame")}
    primary_rows = []
    prev_cx, prev_cy = None, None
    for f in frames:
        candidates = prod_by_frame.get(f)
        if candidates is None or candidates.empty:
            primary_rows.append({"cx": np.nan, "cy": np.nan, "w": np.nan, "h": np.nan})
            continue
        if prev_cx is not None:
            d = np.sqrt((candidates["cx"] - prev_cx) ** 2 + (candidates["cy"] - prev_cy) ** 2)
            near = candidates[d <= max_jump_px]
            if not near.empty:
                chosen = near.sort_values("area", ascending=False).iloc[0]
            else:
                # Nothing plausible near the last known position - this is a
                # break in continuity (occlusion, detector miss, or a
                # completely different blob). Do NOT silently substitute the
                # largest-but-distant blob (that fabricates impossible
                # motion - verified empirically, see module docstring).
                # Mark this frame as missing and reset continuity so the
                # NEXT frame starts fresh rather than inheriting a bad jump.
                primary_rows.append({"cx": np.nan, "cy": np.nan, "w": np.nan, "h": np.nan})
                prev_cx, prev_cy = None, None
                continue
        else:
            chosen = candidates.sort_values("area", ascending=False).iloc[0]
        primary_rows.append({"cx": chosen["cx"], "cy": chosen["cy"], "w": chosen["w"], "h": chosen["h"]})
        prev_cx, prev_cy = chosen["cx"], chosen["cy"]

    primary = pd.DataFrame(primary_rows, index=frames)

    # --- Nearest person distance per frame (to primary product centroid) ---
    persons = df[df["class"] == "person"][["frame", "cx", "cy"]]
    nearest_dist = []
    for f in frames:
        if pd.isna(primary.loc[f, "cx"]) if f in primary.index else True:
            nearest_dist.append(np.nan)
            continue
        pcx, pcy = primary.loc[f, "cx"], primary.loc[f, "cy"]
        this_frame_people = persons[persons["frame"] == f]
        if this_frame_people.empty:
            nearest_dist.append(np.nan)
            continue
        dists = np.sqrt((this_frame_people["cx"] - pcx) ** 2 + (this_frame_people["cy"] - pcy) ** 2)
        nearest_dist.append(float(dists.min()))

    out = pd.DataFrame({
        "frame": frames,
        "timestamp": frames / fps,
        "product_cx": primary["cx"].values,
        "product_cy": primary["cy"].values,
        "product_w": primary["w"].values,
        "product_h": primary["h"].values,
        "nearest_person_dist": nearest_dist,
    })

    # Interpolate short gaps (product briefly undetected for a few frames -
    # common given blob detector limitations) but do NOT fill long gaps,
    # so we don't invent motion where the object simply isn't visible.
    max_gap = int(fps * 0.5)  # up to 0.5s gap tolerated
    for col in ["product_cx", "product_cy", "product_w", "product_h"]:
        out[col] = out[col].interpolate(method="linear", limit=max_gap, limit_area="inside")

    # Smoothed velocity / acceleration via centered rolling window
    dt = 1.0 / fps
    out["vx"] = out["product_cx"].diff() / dt
    out["vy"] = out["product_cy"].diff() / dt
    out["speed"] = np.sqrt(out["vx"] ** 2 + out["vy"] ** 2)
    out["vertical_velocity"] = out["vy"]  # positive = moving down (image y increases downward)

    out["vx_smooth"] = out["vx"].rolling(smoothing_window, center=True, min_periods=1).mean()
    out["vy_smooth"] = out["vy"].rolling(smoothing_window, center=True, min_periods=1).mean()
    out["speed_smooth"] = out["speed"].rolling(smoothing_window, center=True, min_periods=1).mean()

    out["acceleration"] = out["speed_smooth"].diff() / dt
    out["acceleration_smooth"] = out["acceleration"].rolling(smoothing_window, center=True, min_periods=1).mean()

    # Direction-change magnitude (angle delta between consecutive velocity vectors)
    ang = np.arctan2(out["vy_smooth"], out["vx_smooth"])
    ang_delta = ang.diff().abs()
    ang_delta = np.minimum(ang_delta, 2 * np.pi - ang_delta)  # wrap to [0, pi]
    out["direction_change"] = ang_delta

    # Height above floor proxy: NOT real-world height, just pixel y of box
    # bottom edge - lower on screen (larger y) is closer to "floor" for a
    # roughly top-down/oblique dock camera. Documented pixel-space caveat.
    out["floor_proxy_y"] = out["product_cy"] + out["product_h"] / 2

    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tracking_csv", required=True)
    ap.add_argument("--fps", type=float, default=30.0)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    features = extract_features(args.tracking_csv, args.fps)
    features.to_csv(args.out, index=False)
    print(f"Wrote {len(features)} feature rows -> {args.out}")


if __name__ == "__main__":
    main()
