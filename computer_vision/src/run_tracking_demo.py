"""
Phase 3+4 demo - proves the detection+tracking stack works end-to-end on a
real uploaded video. Produces:
  outputs/tracking/<video_name>_tracking.csv
  outputs/annotated_videos/<video_name>_tracked.mp4

Usage:
    python src/run_tracking_demo.py --video data/raw_videos/Rolling_and_dropping_carton.mp4
"""

import argparse
import csv
import os
import sys
import time

import cv2
import yaml

sys.path.insert(0, os.path.dirname(__file__))
from detection import ProductBlobDetector, YoloWorldProductDetector, Detection
from tracking import PersonByteTracker, SimpleIOUTracker


def load_content_roi(video_name, config_path="config/content_roi.yaml"):
    """Returns (x1,y1,x2,y2) content ROI for this video, or None (use full frame)."""
    if not os.path.exists(config_path):
        return None
    with open(config_path) as f:
        cfg = yaml.safe_load(f)
    entry = (cfg.get("content_roi") or {}).get(video_name)
    if entry is None:
        return None
    return tuple(entry["roi"])


COLORS = {"person": (60, 180, 255), "product": (60, 255, 120)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--out_dir", default="outputs")
    ap.add_argument("--frame_skip", type=int, default=1, help="process every Nth frame (speed vs temporal resolution tradeoff)")
    ap.add_argument("--product_detector", choices=["blob", "yolo_world"], default="blob",
                     help="blob = background-subtraction proxy (verified broken on busy scenes, see "
                          "data/annotations/detection_findings.md). yolo_world = open-vocab pretrained "
                          "detector (recommended - test it works on your machine first, see README).")
    args = ap.parse_args()

    video_name = os.path.splitext(os.path.basename(args.video))[0]
    cap_probe = cv2.VideoCapture(args.video)
    fps = cap_probe.get(cv2.CAP_PROP_FPS) or 25
    width = int(cap_probe.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap_probe.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap_probe.release()

    os.makedirs(os.path.join(args.out_dir, "tracking"), exist_ok=True)
    os.makedirs(os.path.join(args.out_dir, "annotated_videos"), exist_ok=True)
    csv_path = os.path.join(args.out_dir, "tracking", f"{video_name}_tracking.csv")
    video_out_path = os.path.join(args.out_dir, "annotated_videos", f"{video_name}_tracked.mp4")

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(video_out_path, fourcc, fps, (width, height))

    person_tracker = PersonByteTracker(model_path="yolo11n-pose.pt", conf_threshold=0.35, device="cpu")
    if args.product_detector == "yolo_world":
        product_detector = YoloWorldProductDetector()
        print("Using YoloWorldProductDetector (open-vocabulary, class-based)")
    else:
        product_detector = ProductBlobDetector(min_area=1500)
        print("Using ProductBlobDetector (motion-based proxy - "
              "see data/annotations/detection_findings.md for known limitations)")
    product_tracker = SimpleIOUTracker(iou_threshold=0.15, max_missed=10, max_centroid_dist=80)

    content_roi = load_content_roi(video_name)
    if content_roi:
        print(f"Using content ROI (excluding NVMS UI chrome): {content_roi}")
    else:
        print("No content ROI configured for this video - using full frame (UI chrome may cause false blobs).")

    csv_rows = []
    t0 = time.time()
    n_frames = 0

    for frame_idx, frame, person_dets in person_tracker.track_video(args.video, content_roi=content_roi, frame_skip=args.frame_skip):
        n_frames += 1
        timestamp = frame_idx / fps

        person_boxes = [(p["x1"], p["y1"], p["x2"], p["y2"]) for p in person_dets]

        if content_roi:
            rx1, ry1, rx2, ry2 = content_roi
            roi_frame = frame[ry1:ry2, rx1:rx2]
            # shift person boxes into ROI-local coords for exclusion check
            roi_person_boxes = [(x1 - rx1, y1 - ry1, x2 - rx1, y2 - ry1) for (x1, y1, x2, y2) in person_boxes]
            roi_dets = product_detector.detect(roi_frame, exclude_boxes=roi_person_boxes)
            # shift detections back to full-frame coords
            product_dets = [
                Detection(d.cls, d.conf, d.x1 + rx1, d.y1 + ry1, d.x2 + rx1, d.y2 + ry1, d.keypoints)
                for d in roi_dets
            ]
        else:
            product_dets = product_detector.detect(frame, exclude_boxes=person_boxes)

        product_tracks = product_tracker.update(product_dets)

        for p in person_dets:
            # Ankle keypoints (COCO pose indices 15=left_ankle, 16=right_ankle),
            # appended as extra trailing columns - added for stepping_on_carton
            # (see behaviour.py / features.load_person_ankle_points). Existing
            # consumers reading the first 11 columns by name are unaffected.
            kpts = p.get("keypoints")
            if kpts is not None and len(kpts) >= 17:
                la_x, la_y = kpts[15]
                ra_x, ra_y = kpts[16]
            else:
                la_x = la_y = ra_x = ra_y = ""

            csv_rows.append([
                frame_idx, round(timestamp, 3), f"person_{p['track_id']}", "person",
                round(p["x1"], 1), round(p["y1"], 1),
                round(p["x2"] - p["x1"], 1), round(p["y2"] - p["y1"], 1),
                round(p["cx"], 1), round(p["cy"], 1), round(p["conf"], 3),
                la_x, la_y, ra_x, ra_y,
            ])
            cv2.rectangle(frame, (int(p["x1"]), int(p["y1"])), (int(p["x2"]), int(p["y2"])), COLORS["person"], 2)
            cv2.putText(frame, f"PERSON #{p['track_id']}", (int(p["x1"]), int(p["y1"]) - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, COLORS["person"], 2)

        for pr in product_tracks:
            csv_rows.append([
                frame_idx, round(timestamp, 3), f"product_{pr['track_id']}", "product",
                round(pr["x1"], 1), round(pr["y1"], 1),
                round(pr["x2"] - pr["x1"], 1), round(pr["y2"] - pr["y1"], 1),
                round(pr["cx"], 1), round(pr["cy"], 1), round(pr["conf"], 3),
                "", "", "", "",  # no ankle keypoints for product rows
            ])
            cv2.rectangle(frame, (int(pr["x1"]), int(pr["y1"])), (int(pr["x2"]), int(pr["y2"])), COLORS["product"], 2)
            cv2.putText(frame, f"PRODUCT #{pr['track_id']}", (int(pr["x1"]), int(pr["y1"]) - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, COLORS["product"], 2)

        cv2.putText(frame, f"t={timestamp:.2f}s", (10, height - 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        writer.write(frame)

    writer.release()
    elapsed = time.time() - t0

    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["frame", "timestamp", "object_id", "class", "x", "y", "w", "h", "cx", "cy", "confidence",
                    "left_ankle_x", "left_ankle_y", "right_ankle_x", "right_ankle_y"])
        w.writerows(csv_rows)

    print(f"Processed {n_frames} frames in {elapsed:.1f}s ({n_frames/elapsed:.1f} FPS on this CPU)")
    print(f"Tracking CSV -> {csv_path} ({len(csv_rows)} rows)")
    print(f"Annotated video -> {video_out_path}")


if __name__ == "__main__":
    main()
