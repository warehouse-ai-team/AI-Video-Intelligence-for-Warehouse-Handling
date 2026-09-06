"""
Synthetic-fixture tests for behaviour.py. (Member 2 - Behaviour Intelligence)

WHY SYNTHETIC: we don't yet have a validated real tracking.csv (the product
detector feeding the real pipeline is still the unreliable blob detector -
see data/annotations/detection_findings.md). These tests do NOT prove the
rules work on real footage; they prove each rule's LOGIC fires on the
motion pattern it's designed to detect, and doesn't crash on missing data
(no ankle keypoints, no ROI config, etc). Real accuracy validation happens
via src/evaluation.py once Member 1 validates YOLO-World and the 6 real
videos are re-processed.

Run:
    cd computer_vision
    python -m tests.test_behaviour_synthetic
"""

import csv
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import behaviour
import features as features_mod
import evaluation
import events as events_mod

FPS = 30
TRACKING_COLUMNS = ["frame", "timestamp", "object_id", "class", "x", "y", "w", "h",
                     "cx", "cy", "confidence", "left_ankle_x", "left_ankle_y",
                     "right_ankle_x", "right_ankle_y"]


def _row(frame, obj_id, cls, x, y, w, h, ankles=None):
    cx, cy = x + w / 2, y + h / 2
    la = ankles[0] if ankles else ("", "")
    ra = ankles[1] if ankles else ("", "")
    return [frame, round(frame / FPS, 3), obj_id, cls, x, y, w, h, cx, cy, 0.8, *la, *ra]


def write_tracking_csv(path, rows):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(TRACKING_COLUMNS)
        w.writerows(rows)


def load_thresholds(config, behaviour_name):
    return config["behaviours"][behaviour_name].get("thresholds", {})


PASS, FAIL = [], []


def check(name, condition, detail=""):
    if condition:
        PASS.append(name)
        print(f"  PASS  {name}")
    else:
        FAIL.append(name)
        print(f"  FAIL  {name}  {detail}")


def test_dropping(config, tmp):
    rows = []
    for f in range(0, 10):  # falling: cy 300 -> 600
        cy_top = 300 + f * 30
        rows.append(_row(f, "product_1", "product", 500, cy_top, 100, 100))
    for f in range(10, 25):  # stopped
        rows.append(_row(f, "product_1", "product", 500, 600, 100, 100))
    tcsv = os.path.join(tmp, "drop_tracking.csv")
    write_tracking_csv(tcsv, rows)
    feat = features_mod.extract_features(tcsv, FPS)
    t = load_thresholds(config, "dropping")
    out = behaviour.detect_dropping(feat, FPS, t)
    check("dropping: fires on sustained fall + stop", len(out) >= 1, out)


def test_throwing(config, tmp):
    rows = []
    for f in range(0, 20):
        rows.append(_row(f, "person_1", "person", 480, 550, 60, 150))
    for f in range(0, 6):  # fast horizontal release away from person
        rows.append(_row(f, "product_1", "product", 500 + f * 80, 300, 60, 60))
    tcsv = os.path.join(tmp, "throw_tracking.csv")
    write_tracking_csv(tcsv, rows)
    feat = features_mod.extract_features(tcsv, FPS)
    t = load_thresholds(config, "throwing")
    out = behaviour.detect_throwing(feat, FPS, t)
    check("throwing: fires on fast outward horizontal release", len(out) >= 1, out)


def test_dragging(config, tmp):
    rows = []
    for f in range(0, 20):
        rows.append(_row(f, "person_1", "person", 500, 550, 60, 150))
    for f in range(0, 20):  # low in frame, moving horizontally, near person
        rows.append(_row(f, "product_1", "product", 480 + f * 6, 600, 100, 60))
    tcsv = os.path.join(tmp, "drag_tracking.csv")
    write_tracking_csv(tcsv, rows)
    feat = features_mod.extract_features(tcsv, FPS)
    t = load_thresholds(config, "dragging")
    out = behaviour.detect_dragging(feat, FPS, t)
    check("dragging: fires on sustained low+horizontal+near-person motion", len(out) >= 1, out)


def test_rough_handling(config, tmp):
    rows = []
    # A sharp, size-normalized-large acceleration + direction reversal
    # ("shaken"/jolted product), not a smooth back-and-forth (which a
    # centered rolling average would cancel out to ~0 - verified during
    # fixture design that a period-2 zigzag does NOT trigger this rule).
    xs = [500, 700, 900, 1100, 900, 700, 500, 300, 100, 300, 500, 700]
    for f, x in enumerate(xs):
        rows.append(_row(f, "product_1", "product", x, 300, 100, 100))
    tcsv = os.path.join(tmp, "rough_tracking.csv")
    write_tracking_csv(tcsv, rows)
    feat = features_mod.extract_features(tcsv, FPS)
    t = load_thresholds(config, "rough_handling")
    out = behaviour.detect_rough_handling(feat, FPS, t)
    check("rough_handling: fires on zig-zag high-acceleration motion", len(out) >= 1, out)


def test_improper_stacking(config, tmp):
    rows = []
    for f in range(0, 35):
        rows.append(_row(f, "product_upper", "product", 500, 300, 120, 80))   # small, upper
        rows.append(_row(f, "product_lower", "product", 490, 400, 100, 60))   # smaller area, lower
    tcsv = os.path.join(tmp, "stack_tracking.csv")
    write_tracking_csv(tcsv, rows)
    boxes = features_mod.load_all_product_boxes(tcsv)
    t = load_thresholds(config, "improper_stacking")
    out = behaviour.detect_improper_stacking(boxes, FPS, t)
    check("improper_stacking: fires when upper item is larger than lower", len(out) >= 1, out)


def test_unstable_stacking(config, tmp):
    rows = []
    for f in range(0, 20):
        rows.append(_row(f, "product_upper", "product", 540, 300, 80, 80))    # offset right, still overlapping enough to count as "stacked"
        rows.append(_row(f, "product_lower", "product", 480, 380, 100, 60))
    tcsv = os.path.join(tmp, "unstable_tracking.csv")
    write_tracking_csv(tcsv, rows)
    boxes = features_mod.load_all_product_boxes(tcsv)
    t = load_thresholds(config, "unstable_stacking")
    out = behaviour.detect_unstable_stacking(boxes, FPS, t)
    check("unstable_stacking: fires when upper item overhangs the base", len(out) >= 1, out)


def test_outside_designated_area(config, tmp):
    rows = []
    for f in range(0, 20):  # product drifts outside an allowed zone
        rows.append(_row(f, "product_1", "product", 900 + f * 5, 300, 60, 60))
    tcsv = os.path.join(tmp, "roi_tracking.csv")
    write_tracking_csv(tcsv, rows)
    feat = features_mod.extract_features(tcsv, FPS)
    t = load_thresholds(config, "outside_designated_area")
    allowed_zone = (0, 0, 800, 720)  # product's x quickly exceeds 800
    out = behaviour.detect_outside_designated_area(feat, FPS, allowed_zone, t)
    check("outside_designated_area: fires once product leaves configured zone", len(out) >= 1, out)
    out_none = behaviour.detect_outside_designated_area(feat, FPS, None, t)
    check("outside_designated_area: returns [] gracefully with no zone configured", out_none == [])


def test_strap_assisted_handling(config, tmp):
    rows = []
    for f in range(0, 20):
        rows.append(_row(f, "person_1", "person", 500 + f * 3, 300, 60, 150))
    for f in range(0, 20):  # moves alongside person at ~constant offset distance
        rows.append(_row(f, "product_1", "product", 620 + f * 3, 310, 80, 80))
    tcsv = os.path.join(tmp, "strap_tracking.csv")
    write_tracking_csv(tcsv, rows)
    feat = features_mod.extract_features(tcsv, FPS)
    t = load_thresholds(config, "strap_assisted_handling")
    out = behaviour.detect_strap_assisted_handling(feat, FPS, t)
    check("strap_assisted_handling: fires on constant-offset sustained motion", len(out) >= 1, out)


def test_stepping_on_carton(config, tmp):
    rows = []
    for f in range(0, 15):
        rows.append(_row(f, "product_1", "product", 500, 500, 150, 80))
        # ankle point sits inside the product bbox for every frame
        rows.append(_row(f, "person_1", "person", 480, 350, 100, 250,
                          ankles=[(560, 540), (0, 0)]))
    tcsv = os.path.join(tmp, "step_tracking.csv")
    write_tracking_csv(tcsv, rows)
    boxes = features_mod.load_all_product_boxes(tcsv)
    ankles = features_mod.load_person_ankle_points(tcsv)
    t = load_thresholds(config, "stepping_on_carton")
    out = behaviour.detect_stepping_on_carton(boxes, ankles, FPS, t)
    check("stepping_on_carton: fires when ankle overlaps carton bbox", len(out) >= 1, out)
    out_no_kpts = behaviour.detect_stepping_on_carton(boxes, {}, FPS, t)
    check("stepping_on_carton: returns [] gracefully with no keypoint data", out_no_kpts == [])


def test_unsafe_loading_sequence(config):
    fake_events = [
        {"behaviour": "improper_stacking", "start_time": 4.0, "end_time": 5.0, "confidence": 0.55,
         "start_frame": 120, "end_frame": 150},
        {"behaviour": "dropping", "start_time": 6.0, "end_time": 6.5, "confidence": 0.8,
         "start_frame": 180, "end_frame": 195},
    ]
    t = load_thresholds(config, "unsafe_loading_sequence")
    out = behaviour.detect_unsafe_loading_sequence(fake_events, config, t)
    check("unsafe_loading_sequence: chains an instability event into a following failure event",
          len(out) == 1, out)


def test_end_to_end_engine_and_evaluation(config, tmp):
    """Full run_behaviour_engine() + events.py + evaluation.py smoke test on the dropping fixture."""
    rows = []
    for f in range(0, 10):
        rows.append(_row(f, "product_1", "product", 500, 300 + f * 30, 100, 100))
    for f in range(10, 25):
        rows.append(_row(f, "product_1", "product", 500, 600, 100, 100))
    tcsv = os.path.join(tmp, "e2e_tracking.csv")
    write_tracking_csv(tcsv, rows)
    fcsv = os.path.join(tmp, "e2e_features.csv")
    features_mod.extract_features(tcsv, FPS).to_csv(fcsv, index=False)

    config_path = os.path.join(tmp, "behaviours.yaml")
    shutil.copy("config/behaviours.yaml", config_path)

    result = behaviour.run_behaviour_engine(fcsv, tcsv, FPS, video_name="SYNTH", config_path=config_path)
    check("end-to-end: engine produces at least one risk-tagged event",
          len(result) >= 1 and all("risk" in e for e in result), result)

    records = events_mod.build_event_records(result, "V_SYNTH")
    events_dir = os.path.join(tmp, "events")
    events_mod.write_events(records, os.path.join(events_dir, "V_SYNTH_events.json"),
                             os.path.join(events_dir, "V_SYNTH_events.csv"))

    gt_path = os.path.join(tmp, "ground_truth.csv")
    with open(gt_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["video_id", "filename", "start_time", "end_time", "behaviour", "risk",
                    "camera", "evidence_type", "notes"])
        w.writerow(["V_SYNTH", "synthetic.mp4", 0.0, 0.5, "dropping", "HIGH", "n/a", "n/a", "synthetic fixture"])

    per_behaviour, fp_report, fn_report, missing = evaluation.evaluate(gt_path, events_dir, iou_thresh=0.05)
    check("evaluation: end-to-end scoring runs and records a dropping TP",
          per_behaviour.get("dropping", {}).get("tp", 0) >= 1, per_behaviour)


def main():
    src_dir = os.path.join(os.path.dirname(__file__), "..")
    os.chdir(src_dir)  # so relative config/ paths resolve like they do in real usage
    config = behaviour.load_behaviour_config("config/behaviours.yaml")

    tmp = tempfile.mkdtemp(prefix="behaviour_test_")
    try:
        test_dropping(config, tmp)
        test_throwing(config, tmp)
        test_dragging(config, tmp)
        test_rough_handling(config, tmp)
        test_improper_stacking(config, tmp)
        test_unstable_stacking(config, tmp)
        test_outside_designated_area(config, tmp)
        test_strap_assisted_handling(config, tmp)
        test_stepping_on_carton(config, tmp)
        test_unsafe_loading_sequence(config)
        test_end_to_end_engine_and_evaluation(config, tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
    if FAIL:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
