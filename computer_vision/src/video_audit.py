"""
Phase 1 - Video Audit
Run this FIRST on every real challenge video before any detection/tracking work.

It does NOT invent anything - it only reports what OpenCV can measure
(duration, fps, resolution) and extracts evenly-spaced sample frames so
a human (or Claude, viewing the frames) can log real objects/behaviours.

Usage:
    python src/video_audit.py --input_dir data/raw_videos --out data/frames --samples 12
"""

import argparse
import os
import csv
import cv2


def audit_video(path, out_dir, n_samples=12):
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        return None

    fps = cap.get(cv2.CAP_PROP_FPS) or 0
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    duration = frame_count / fps if fps > 0 else 0

    video_name = os.path.splitext(os.path.basename(path))[0]
    frame_out_dir = os.path.join(out_dir, video_name)
    os.makedirs(frame_out_dir, exist_ok=True)

    saved = []
    if frame_count > 0 and n_samples > 0:
        step = max(frame_count // n_samples, 1)
        idx = 0
        saved_i = 0
        while idx < frame_count and saved_i < n_samples:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ok, frame = cap.read()
            if ok:
                t = idx / fps if fps > 0 else 0
                fname = f"{video_name}_f{idx:06d}_t{t:.2f}s.jpg"
                cv2.imwrite(os.path.join(frame_out_dir, fname), frame)
                saved.append((idx, round(t, 2), fname))
                saved_i += 1
            idx += step

    cap.release()

    return {
        "video": os.path.basename(path),
        "duration_sec": round(duration, 2),
        "fps": round(fps, 2),
        "frame_count": frame_count,
        "width": width,
        "height": height,
        "sample_frames_dir": frame_out_dir,
        "sample_frames": saved,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input_dir", default="data/raw_videos")
    ap.add_argument("--out", default="data/frames")
    ap.add_argument("--samples", type=int, default=12,
                     help="number of evenly spaced frames to extract per video")
    ap.add_argument("--report", default="data/annotations/video_audit_report.csv")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    os.makedirs(os.path.dirname(args.report), exist_ok=True)

    exts = (".mp4", ".mov", ".avi", ".mkv", ".m4v")
    videos = [f for f in os.listdir(args.input_dir) if f.lower().endswith(exts)]

    if not videos:
        print(f"No video files found in {args.input_dir}")
        print(f"Supported extensions: {exts}")
        return

    rows = []
    for v in sorted(videos):
        path = os.path.join(args.input_dir, v)
        print(f"Auditing: {v} ...")
        result = audit_video(path, args.out, args.samples)
        if result is None:
            print(f"  FAILED to open {v}")
            continue
        print(f"  duration={result['duration_sec']}s fps={result['fps']} "
              f"res={result['width']}x{result['height']} "
              f"frames_extracted={len(result['sample_frames'])} "
              f"-> {result['sample_frames_dir']}")
        rows.append(result)

    with open(args.report, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["video", "duration_sec", "fps", "frame_count", "width", "height", "sample_frames_dir"])
        for r in rows:
            w.writerow([r["video"], r["duration_sec"], r["fps"], r["frame_count"],
                        r["width"], r["height"], r["sample_frames_dir"]])

    print(f"\nAudit report written to {args.report}")
    print("Next step: view the extracted sample frames and log real objects/behaviours "
          "into data/annotations/ground_truth.csv (see README Phase 1).")


if __name__ == "__main__":
    main()
