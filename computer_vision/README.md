# Warehouse CV Module — Member 1 (Computer Vision / Video Intelligence)

Status: **Phases 1-7 built and tested against your real 6 videos. One
architectural pivot required before the behaviour engine's output can be
trusted — see below.**

Read `data/annotations/detection_findings.md` first — it's the honest,
verified record of what works, what was tried and failed, and why. This
README summarizes it; that file has the receipts.

## TL;DR status

| Phase | Status |
|---|---|
| 1. Video audit | Done. Real metadata + ground truth for all 6 clips (`data/annotations/ground_truth.csv`) |
| 3. Person detection | Verified working (pretrained YOLO) |
| 4. Person tracking | Working, real ID churn documented (not hidden) |
| 3/5. Product detection | Motion-blob proxy verified BROKEN on busy scenes. YOLO-World built but needs YOU to test (sandbox network-restricted) |
| 5. Motion features | Built, logic sound, currently fed unreliable product input |
| 6. Behaviour engine | Logic built (dropping/throwing/dragging/rough_handling), do not trust current output until product detection is fixed |
| 7. Event JSON/CSV | Schema built and working, same caveat as above |
| 8-9. Clips/pipeline/eval | Not started - blocked on product detection fix |

## THE ONE THING YOU NEED TO DO FIRST

Test YOLO-World on your machine (needs normal internet - it failed in my
sandbox only because CLIP's weight host isn't on the sandbox's restricted
allowlist):

```powershell
pip install ultralytics
python -c "from ultralytics import YOLO; m = YOLO('yolov8s-world.pt'); m.set_classes(['cardboard box','mattress','pallet']); r = m.predict('data/frames/Throwing_Mattresses/Throwing_Mattresses_f000267_t8.90s.jpg'); r[0].show()"
```

If it draws a box around the mattress: run the full pipeline with
`--product_detector yolo_world` (see below) and the behaviour engine's
output becomes trustworthy. If it's too slow or unreliable: tell me and
we pivot to a small custom-trained model (very feasible, see findings doc).

## Environment Setup (Windows)

```powershell
python -m venv venv
venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Running the pipeline (per video, for now — Phase 9 will add batch mode)

```powershell
# Default (motion-blob proxy - fast, no internet, but verified unreliable for behaviour detection):
python src/run_tracking_demo.py --video data/raw_videos/Throwing_Mattresses.mp4 --frame_skip 1

# Once YOLO-World is confirmed working on your machine:
python src/run_tracking_demo.py --video data/raw_videos/Throwing_Mattresses.mp4 --product_detector yolo_world

# Then extract features and run the behaviour engine:
python src/features.py --tracking_csv outputs/tracking/Throwing_Mattresses_tracking.csv --fps 30 --out outputs/tracking/Throwing_Mattresses_features.csv
python -c "
from src.behaviour import run_behaviour_engine
from src.events import build_event_records, write_events
events = run_behaviour_engine('outputs/tracking/Throwing_Mattresses_features.csv', fps=30)
records = build_event_records(events, 'V006')
write_events(records, 'outputs/events/events.json', 'outputs/events/events.csv')
print(len(events), 'events detected')
"
```

## Real ground truth (for evaluating your own results against)

`data/annotations/ground_truth.csv` — built by manually reviewing extracted
sample frames per video (`data/frames/<video_name>/`), not invented. Use
this to check the behaviour engine's precision/recall once product
detection is fixed (Phase 9 - evaluation.py - not yet built).

## Project Structure

```
warehouse_cv/
├── data/
│   ├── raw_videos/        <- your 6 uploaded videos
│   ├── frames/            <- Phase 1 sample frames per video
│   ├── annotations/
│   │   ├── ground_truth.csv           <- real, timestamped
│   │   ├── video_audit_report.csv     <- real OpenCV metadata
│   │   └── detection_findings.md      <- READ THIS FIRST
│   └── dataset/
├── config/
│   ├── behaviours.yaml    <- taxonomy + risk levels
│   ├── settings.yaml
│   └── content_roi.yaml   <- per-video crop excluding NVMS UI chrome
├── src/
│   ├── video_audit.py     <- Phase 1, done
│   ├── detection.py       <- Phase 3/5: PersonDetector (verified), YoloWorldProductDetector (test me), ProductBlobDetector (broken, kept as fallback)
│   ├── tracking.py        <- Phase 4: PersonByteTracker (verified), SimpleIOUTracker (works for whatever detector feeds it)
│   ├── features.py        <- Phase 5: motion feature extraction (logic verified, needs good input)
│   ├── behaviour.py       <- Phase 6: rule-based behaviour engine (logic verified, needs good input)
│   ├── events.py          <- Phase 7: JSON/CSV event schema (verified)
│   ├── run_tracking_demo.py <- combined Phase 3+4 runner, use this
│   ├── clips.py            <- Phase 8, NOT YET BUILT
│   ├── visualization.py    <- Phase 8, partially done (boxes+IDs in run_tracking_demo.py; behaviour/risk overlay NOT done)
│   ├── evaluation.py       <- Phase 9, NOT YET BUILT
│   └── pipeline.py         <- Phase 8 single-command entry point, NOT YET BUILT (build after product detection is fixed)
├── outputs/
│   ├── annotated_videos/  <- real outputs from all 6 videos
│   ├── tracking/          <- real tracking.csv + features.csv for all 6 videos
│   ├── events/            <- events.json/csv (untrustworthy until product detection fixed)
│   └── clips/, screenshots/  <- empty, Phase 8 not built yet
├── requirements.txt
└── README.md
```

## Next steps, in order

1. **You**: test YOLO-World locally (5 minutes, see above). Report back what you see.
2. **Me**: once confirmed, re-run all 6 videos with `--product_detector yolo_world`, regenerate features/events, and check the behaviour engine's output against `ground_truth.csv` for real (Phase 9 - evaluation.py).
3. **Me**: build `clips.py` (incident clip extraction) and `pipeline.py` (single-command entry point) once the detection layer is trustworthy — no point building on top of unreliable input.
4. **Me**: extend `visualization.py` to overlay behaviour/risk/confidence on the annotated video (currently only shows PERSON/PRODUCT boxes+IDs).
5. If YOLO-World doesn't work well on your machine: small custom-trained YOLO (50-100 annotated frames, 2-3 classes) — fallback plan already documented in `detection_findings.md`.
