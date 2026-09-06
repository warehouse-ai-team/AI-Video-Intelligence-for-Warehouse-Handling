# Behaviour Intelligence — Status (Member 2)

## What changed in this pass

1. **All 10 behaviours now have a rule-based detector** in `src/behaviour.py`
   (was 4). New: `improper_stacking`, `unstable_stacking`,
   `outside_designated_area` (inactive until ROI coords are set),
   `strap_assisted_handling` (low-confidence proxy), `stepping_on_carton`
   (needs ankle keypoints), `unsafe_loading_sequence` (chains other events).
2. **The original 4 rules were tightened**, not just left alone:
   - `dropping` now requires a real net vertical displacement, not just an
     instantaneous velocity spike (filters jitter).
   - `throwing` now requires the motion to be mostly *horizontal* and to
     span several consecutive frames — targets the exact false-positive
     mode Member 1 documented ("fires almost continuously on busy scenes").
   - `rough_handling` acceleration is now normalized by object size
     (`/√area`) instead of raw pixels, so a mattress and a small box use
     the same threshold fairly.
   - Fixed an off-by-one bug where a single-frame detection window always
     computed `duration = 0` and got silently dropped.
   - Added cross-behaviour suppression: an overlapping `dropping` +
     `rough_handling` pair (a hard drop trips both) now keeps only the
     higher-confidence one instead of double-counting.
3. **All thresholds moved out of code and into `config/behaviours.yaml`**
   under a `thresholds:` block per behaviour, so tuning after running
   evaluation is a config edit, not a code change.
4. **`src/evaluation.py` (Phase 9) is built** — scores any set of detected
   events against `data/annotations/ground_truth.csv` (temporal IoU
   matching per behaviour) and prints precision/recall/F1 plus a
   false-positive/false-negative list to guide threshold tuning.
5. **`tests/test_behaviour_synthetic.py` is built** — synthetic tracking
   data per behaviour, proves each rule fires on the pattern it's designed
   for and fails gracefully (not crash) when data it needs (ROI config,
   ankle keypoints) isn't available yet. All 14 checks pass.
6. **`run_tracking_demo.py` now writes ankle keypoints** (left/right, from
   the pose model already in use) as 4 extra trailing columns in
   `tracking.csv` — needed for `stepping_on_carton`. Backward compatible:
   older consumers reading the first 11 columns by name are unaffected.
7. **`features.py` gained two new helpers**: `load_all_product_boxes`
   (every product box per frame, not just the single "primary product" —
   needed for the two stacking rules) and `load_person_ankle_points`.

## What I could NOT validate yet, and why

I have no real tracking data to run this against. The 6 real videos'
tracking.csv files were generated with the blob-based product detector,
which Member 1's own findings doc confirms is unreliable (fires
"throwing" on non-throwing footage). So:

- Every threshold in `behaviours.yaml` is a documented **starting point**
  (physics reasoning + passing the synthetic fixtures), not something
  tuned against real footage precision/recall.
- `outside_designated_area` will not fire on anything until someone (any
  of us) fills in `roi_zones` in `behaviours.yaml` with real per-camera
  zone coordinates — same process Member 1 used for `content_roi.yaml`.
- `stepping_on_carton` needs the new ankle-keypoint columns, which only
  exist for tracking.csv files generated *after* this change — the 6
  existing real tracking.csv files need to be regenerated to pick them up.

## What I need from Member 1 to finish validating

1. Re-run `run_tracking_demo.py --product_detector yolo_world` on all 6
   real videos (once YOLO-World is confirmed working) so I get real
   multi-product tracking data + the new ankle-keypoint columns.
2. Then I run `src/evaluation.py` against the real `events.json` output
   and `ground_truth.csv`, and tune `behaviours.yaml` thresholds against
   the real false-positive/false-negative list it prints.

## How to run things

```bash
cd computer_vision

# Unit tests (no video/model needed, runs in seconds):
python -m tests.test_behaviour_synthetic

# Full pipeline for one real video, once tracking.csv/features.csv exist:
python -c "
from src.behaviour import run_behaviour_engine
from src.events import build_event_records, write_events
events = run_behaviour_engine(
    'outputs/tracking/Throwing_Mattresses_features.csv',
    'outputs/tracking/Throwing_Mattresses_tracking.csv',
    fps=30, video_name='Throwing_Mattresses',
)
records = build_event_records(events, 'V006')
write_events(records, 'outputs/events/V006_events.json', 'outputs/events/V006_events.csv')
"

# Score against ground truth once events exist for a video (or all 6):
python src/evaluation.py --ground_truth data/annotations/ground_truth.csv --events_dir outputs/events
```

Note the `run_behaviour_engine` call signature changed: it now takes
`(features_csv, tracking_csv, fps, video_name=..., config_path=...)`
instead of just `(features_csv, fps)`, because the new multi-product and
keypoint-based rules need the raw tracking CSV, not just the
single-primary-product features CSV.
