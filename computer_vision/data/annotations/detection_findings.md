# Detection & Tracking Findings (from real footage, not assumptions)

This log exists so decisions aren't re-litigated or silently forgotten.
Every claim below was verified by running code against the 6 uploaded
videos, not assumed from general CV knowledge.

## 1. Footage nature
All 6 clips are screen-recordings (5) or a phone photo (1) of an NVMS
playback tool already used for internal RCA review - not raw CCTV exports.
They carry burned-in circles/arrows/captions naming the exact violation.
Used to build `data/annotations/ground_truth.csv`; NOT used as a detection
signal (real judging footage won't have captions).

## 2. Person detection - WORKS
Pretrained YOLO (COCO class 0) reliably detects people, conf 0.5-0.85,
across all 6 videos, no training needed.

## 3. Person tracking - WORKS, WITH REAL LIMITATIONS
ByteTrack (via ultralytics `model.track(..., persist=True)`), run per-frame
with content-ROI pre-cropping (`config/content_roi.yaml`) to exclude NVMS UI
chrome and, on the split-screen clip, the second camera feed.
- ID churn observed: 15-18 unique IDs for ~4-5 real people in a 6-9s clip.
- Root causes identified: compression/re-recording artifacts, and (before
  the ROI fix) two independent camera feeds being tracked as one scene.
- Cropping to content ROI improved but did not eliminate churn (18->15 on
  the worst clip). Acceptable for now; behaviour rules should not assume
  any person ID survives an entire clip.

## 4. Product/carton/mattress/pallet detection - TWO ATTEMPTS

### Attempt A: COCO YOLO - FAILED (as expected)
No COCO class exists for carton/box/mattress/pallet. Confirmed by running
detection on real frames from 3 different videos: zero relevant boxes.

### Attempt B: Background-subtraction blob proxy - FAILED for behaviour detection
Built `ProductBlobDetector` (MOG2 + contour filtering) with a "largest/
nearest-continuity blob = the product" heuristic. Iteratively fixed:
- Initial version: 100-205 spurious track IDs per clip, traced to blinking
  NVMS UI icons and ticking timestamp digits being read as motion. Fixed
  with content-ROI cropping (127 -> 68 IDs on one test clip).
- Still produced physically-impossible velocity spikes (blob position
  jumping >900px in one frame) when the "nearest" blob search failed and
  fell back to "largest blob anywhere" - fixed by treating a failed
  continuity match as a data gap (NaN) instead of substituting a distant
  blob.
- FINAL VERDICT (confirmed by running the full pipeline on all 6 videos,
  not just one): even after all fixes, the behaviour engine fired
  "throwing" almost continuously on every single video, including clips
  with no throwing at all (dragging, stacking clips). Root cause: these are
  busy dock scenes with constant ambient foot traffic and other real motion
  (other workers, hand trucks) in frame throughout. A motion-blob detector
  cannot distinguish "the flagged carton" from "a person walking through
  the background" - both are just moving blobs of similar size. This is an
  architectural limitation, not a threshold-tuning problem, and no amount
  of further threshold adjustment will fix it.

### Attempt C: YOLO-World (open-vocabulary pretrained) - NOT YET VERIFIED
Recommended next step. Detects by semantic class ("cardboard box",
"mattress", "pallet") instead of by motion, so it doesn't have Attempt B's
failure mode. Could not be tested inside the build sandbox because CLIP's
weight host is outside the sandbox's restricted network allowlist - this is
a sandbox limitation, not a fundamental one. Test on a normal machine:

    pip install ultralytics
    python -c "
    from ultralytics import YOLO
    m = YOLO('yolov8s-world.pt')
    m.set_classes(['cardboard box','mattress','pallet','pallet jack'])
    r = m.predict('data/frames/Throwing_Mattresses/Throwing_Mattresses_f000267_t8.90s.jpg')
    r[0].show()
    "

If boxes appear around the mattress: swap `YoloWorldProductDetector` in for
`ProductBlobDetector` in `src/run_tracking_demo.py` (one line - both share
the same `Detection` interface) and re-run the whole pipeline.

If YOLO-World is too slow/unreliable on your hardware: the fallback plan is
a small custom-trained YOLO (50-100 annotated frames across the 6 videos,
2-3 classes: carton, mattress, pallet) - very feasible in a few hours via
Roboflow, and the training/inference code pattern is identical to what
`detection.py` already does for the person detector.

## 5. Behaviour engine - LOGIC BUILT, ACCURACY UNVERIFIED PENDING FIX #4
`src/behaviour.py` implements dropping/throwing/dragging/rough_handling as
temporal-window rules over smoothed velocity/acceleration/proximity
features. The rule LOGIC is sound and reusable regardless of which product
detector feeds it - but it is currently being fed unreliable input (Attempt
B above), so its output (`outputs/events/events.csv`) is NOT currently
trustworthy and should be re-generated once Attempt C (or a custom model)
is validated. Do not demo the current events.csv as-is.
