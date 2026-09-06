"""
Phase 9 - Evaluation. (Member 2 - Behaviour Intelligence)

Compares detected behaviour events (events.json/csv, produced by
behaviour.py + events.py) against the hand-labeled
data/annotations/ground_truth.csv, and reports precision/recall/F1 per
behaviour so thresholds in config/behaviours.yaml can be tuned against
real numbers instead of guesswork.

Matching rule: a predicted event and a ground-truth row are a match if
they name the SAME behaviour AND their [start_time, end_time] intervals
overlap by at least `iou_thresh` (temporal IoU). Matching is greedy,
highest-IoU-first, one-to-one (a predicted event can match at most one
ground-truth row and vice versa). Everything predicted that doesn't match
is a false positive; every ground-truth row that doesn't get matched is a
false negative.

NOTE ON iou_thresh: ground-truth windows here were hand-labeled to the
nearest ~second from screen recordings, not frame-accurate. A strict IoU
(e.g. 0.5) is too harsh for this kind of label. Default is deliberately
loose (0.1) - tightening it is itself a legitimate way to make the
evaluation stricter as detection quality improves.

Usage:
    python src/evaluation.py \\
        --ground_truth data/annotations/ground_truth.csv \\
        --events_dir outputs/events \\
        --iou_thresh 0.1

Expects one events JSON per video in --events_dir, named
<video_id>_events.json (list of records shaped like events.py's output,
each with at least behaviour/start_time/end_time/confidence). Videos with
no events file are skipped with a warning, not a crash.
"""

import argparse
import csv
import json
import os
from collections import defaultdict


def load_ground_truth(path):
    """Returns {video_id: [{behaviour,start_time,end_time}, ...]}"""
    gt = defaultdict(list)
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            gt[row["video_id"]].append({
                "behaviour": row["behaviour"].strip(),
                "start_time": float(row["start_time"]),
                "end_time": float(row["end_time"]),
            })
    return gt


def load_predicted_events(events_dir, video_id):
    path = os.path.join(events_dir, f"{video_id}_events.json")
    if not os.path.exists(path):
        return None  # signals "no predictions available", distinct from "zero events"
    with open(path) as f:
        records = json.load(f)
    return [{"behaviour": r["behaviour"], "start_time": r["start_time"], "end_time": r["end_time"],
              "confidence": r.get("confidence")} for r in records]


def _time_iou(a, b):
    inter = max(0.0, min(a["end_time"], b["end_time"]) - max(a["start_time"], b["start_time"]))
    union = max(a["end_time"], b["end_time"]) - min(a["start_time"], b["start_time"])
    return inter / union if union > 0 else 0.0


def match_events(predicted, ground_truth, iou_thresh=0.1):
    """
    Greedy one-to-one matching, highest-IoU pairs first, same behaviour
    label required. Returns (matches, false_positives, false_negatives)
    where matches is [(pred, gt, iou), ...].
    """
    candidates = []
    for pi, p in enumerate(predicted):
        for gi, g in enumerate(ground_truth):
            if p["behaviour"] != g["behaviour"]:
                continue
            iou = _time_iou(p, g)
            if iou >= iou_thresh:
                candidates.append((iou, pi, gi))
    candidates.sort(reverse=True, key=lambda c: c[0])

    matched_pred, matched_gt = set(), set()
    matches = []
    for iou, pi, gi in candidates:
        if pi in matched_pred or gi in matched_gt:
            continue
        matched_pred.add(pi)
        matched_gt.add(gi)
        matches.append((predicted[pi], ground_truth[gi], iou))

    false_positives = [p for pi, p in enumerate(predicted) if pi not in matched_pred]
    false_negatives = [g for gi, g in enumerate(ground_truth) if gi not in matched_gt]
    return matches, false_positives, false_negatives


def evaluate(ground_truth_path, events_dir, iou_thresh=0.1):
    gt_by_video = load_ground_truth(ground_truth_path)

    per_behaviour = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0})
    fp_report, fn_report = [], []
    videos_missing_predictions = []

    for video_id, gt_rows in gt_by_video.items():
        predicted = load_predicted_events(events_dir, video_id)
        if predicted is None:
            videos_missing_predictions.append(video_id)
            for g in gt_rows:
                per_behaviour[g["behaviour"]]["fn"] += 1
                fn_report.append({"video_id": video_id, **g, "note": "no events file found"})
            continue

        matches, fps, fns = match_events(predicted, gt_rows, iou_thresh)
        for pred, gt, iou in matches:
            per_behaviour[gt["behaviour"]]["tp"] += 1
        for p in fps:
            per_behaviour[p["behaviour"]]["fp"] += 1
            fp_report.append({"video_id": video_id, **p})
        for g in fns:
            per_behaviour[g["behaviour"]]["fn"] += 1
            fn_report.append({"video_id": video_id, **g, "note": "unmatched"})

    return per_behaviour, fp_report, fn_report, videos_missing_predictions


def print_report(per_behaviour, fp_report, fn_report, videos_missing_predictions):
    print("=" * 78)
    print(f"{'Behaviour':<28}{'TP':>5}{'FP':>5}{'FN':>5}{'Precision':>12}{'Recall':>10}{'F1':>8}")
    print("-" * 78)
    total_tp = total_fp = total_fn = 0
    for behaviour in sorted(per_behaviour):
        c = per_behaviour[behaviour]
        tp, fp, fn = c["tp"], c["fp"], c["fn"]
        total_tp += tp
        total_fp += fp
        total_fn += fn
        precision = tp / (tp + fp) if (tp + fp) else float("nan")
        recall = tp / (tp + fn) if (tp + fn) else float("nan")
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) and precision == precision and recall == recall and (precision + recall) > 0 else float("nan")
        print(f"{behaviour:<28}{tp:>5}{fp:>5}{fn:>5}{precision:>12.2f}{recall:>10.2f}{f1:>8.2f}")
    print("-" * 78)
    overall_p = total_tp / (total_tp + total_fp) if (total_tp + total_fp) else float("nan")
    overall_r = total_tp / (total_tp + total_fn) if (total_tp + total_fn) else float("nan")
    overall_f1 = 2 * overall_p * overall_r / (overall_p + overall_r) if (overall_p + overall_r) > 0 else float("nan")
    print(f"{'OVERALL':<28}{total_tp:>5}{total_fp:>5}{total_fn:>5}{overall_p:>12.2f}{overall_r:>10.2f}{overall_f1:>8.2f}")
    print("=" * 78)

    if videos_missing_predictions:
        print(f"\nNo events file found for: {', '.join(videos_missing_predictions)}"
              f" (run the pipeline for these videos first - all their GT rows counted as FN)")

    if fp_report:
        print(f"\nFalse positives ({len(fp_report)}) - candidates for tightening thresholds:")
        for p in fp_report:
            print(f"  [{p['video_id']}] {p['behaviour']:<24} {p['start_time']:.2f}-{p['end_time']:.2f}s"
                  f"  conf={p.get('confidence')}")

    if fn_report:
        print(f"\nFalse negatives ({len(fn_report)}) - candidates for loosening thresholds / new signals:")
        for g in fn_report:
            print(f"  [{g['video_id']}] {g['behaviour']:<24} {g['start_time']:.2f}-{g['end_time']:.2f}s"
                  f"  ({g.get('note')})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ground_truth", default="data/annotations/ground_truth.csv")
    ap.add_argument("--events_dir", default="outputs/events")
    ap.add_argument("--iou_thresh", type=float, default=0.1)
    args = ap.parse_args()

    per_behaviour, fp_report, fn_report, missing = evaluate(
        args.ground_truth, args.events_dir, args.iou_thresh
    )
    print_report(per_behaviour, fp_report, fn_report, missing)


if __name__ == "__main__":
    main()
