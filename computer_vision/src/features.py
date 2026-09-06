"""
Phase 5 - Motion feature extraction (v2 - per-object, not merged).

Reads tracking.csv (frame, timestamp, object_id, class, x, y, w, h, cx, cy,
confidence) and produces features.csv with per-frame, per-tracked-object
motion features.

DESIGN CHANGE FROM v1 (documented, not hidden): the original version merged
all detected products into one "primary product" trajectory per frame. This
worked as a stopgap when product detection was unreliable (blob detector),
but once real product detection went live (custom-trained model), scenes
with multiple genuine simultaneous boxes/pallets caused that merged
trajectory to jump between different real physical objects - indistinguishable
from impossible high-speed motion. Verified empirically: this caused
"throwing" to fire on every single video, including ones with zero throwing.

Fix: compute motion features PER TRACKED object_id (using the IDs the
tracker already assigns), not merged across all products in a frame. Each
tracked object gets its own velocity/acceleration/proximity time series.
Behaviour rules (behaviour.py) now run per-object and tag which object_id
triggered each event.
"""

import argparse
import pandas as pd
import numpy as np


def extract_features(tracking_csv, fps, smoothing_window=5):
    df = pd.read_csv(tracking_csv)
    if df.empty:
        return pd.DataFrame()

    persons = df[df["class"] == "person"][["frame", "cx", "cy"]]
    products = df[df["class"] == "product"].copy()

    if products.empty:
        return pd.DataFrame()

    all_rows = []

    for obj_id, obj_df in products.groupby("object_id"):
        obj_df = obj_df.sort_values("frame").reset_index(drop=True)
        min_frame, max_frame = int(obj_df["frame"].min()), int(obj_df["frame"].max())
        frames = np.arange(min_frame, max_frame + 1)

        # Reindex onto every frame in this object's lifespan, leaving gaps as NaN
        # for frames where this specific track_id wasn't detected (brief misses).
        obj_indexed = obj_df.set_index("frame").reindex(frames)

        out = pd.DataFrame({
            "object_id": obj_id,
            "frame": frames,
            "timestamp": frames / fps,
            "product_cx": obj_indexed["cx"].values,
            "product_cy": obj_indexed["cy"].values,
            "product_w": obj_indexed["w"].values,
            "product_h": obj_indexed["h"].values,
        })

        # Only interpolate short gaps (this object briefly missed a few frames),
        # never bridge a long gap - long gaps usually mean the tracker lost
        # this object and a DIFFERENT object picked up the same ID later
        # (tracker ID reuse), which should NOT be treated as continuous motion.
        max_gap = int(fps * 0.3)
        for col in ["product_cx", "product_cy", "product_w", "product_h"]:
            out[col] = out[col].interpolate(method="linear", limit=max_gap, limit_area="inside")

        # Nearest person distance, per frame, to THIS object specifically
        nearest_dist = []
        for f in frames:
            row = out[out["frame"] == f].iloc[0]
            if pd.isna(row["product_cx"]):
                nearest_dist.append(np.nan)
                continue
            this_frame_people = persons[persons["frame"] == f]
            if this_frame_people.empty:
                nearest_dist.append(np.nan)
                continue
            dists = np.sqrt((this_frame_people["cx"] - row["product_cx"]) ** 2 +
                             (this_frame_people["cy"] - row["product_cy"]) ** 2)
            nearest_dist.append(float(dists.min()))
        out["nearest_person_dist"] = nearest_dist

        dt = 1.0 / fps
        out["vx"] = out["product_cx"].diff() / dt
        out["vy"] = out["product_cy"].diff() / dt
        out["speed"] = np.sqrt(out["vx"] ** 2 + out["vy"] ** 2)
        out["vertical_velocity"] = out["vy"]

        out["vx_smooth"] = out["vx"].rolling(smoothing_window, center=True, min_periods=1).mean()
        out["vy_smooth"] = out["vy"].rolling(smoothing_window, center=True, min_periods=1).mean()
        out["speed_smooth"] = out["speed"].rolling(smoothing_window, center=True, min_periods=1).mean()

        out["acceleration"] = out["speed_smooth"].diff() / dt
        out["acceleration_smooth"] = out["acceleration"].rolling(smoothing_window, center=True, min_periods=1).mean()

        ang = np.arctan2(out["vy_smooth"], out["vx_smooth"])
        ang_delta = ang.diff().abs()
        ang_delta = np.minimum(ang_delta, 2 * np.pi - ang_delta)
        out["direction_change"] = ang_delta

        out["floor_proxy_y"] = out["product_cy"] + out["product_h"] / 2

        all_rows.append(out)

    if not all_rows:
        return pd.DataFrame()

    result = pd.concat(all_rows, ignore_index=True)
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tracking_csv", required=True)
    ap.add_argument("--fps", type=float, default=30.0)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    features = extract_features(args.tracking_csv, args.fps)
    features.to_csv(args.out, index=False)
    print(f"Wrote {len(features)} feature rows across "
          f"{features['object_id'].nunique() if not features.empty else 0} tracked objects -> {args.out}")


if __name__ == "__main__":
    main()
