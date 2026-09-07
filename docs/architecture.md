# Architecture

## Challenge

AI Video Intelligence for Warehouse Handling — detect risky handling
behaviour in loading/unloading footage and generate structured, evidence-
backed alerts (not just recordings for after-the-fact human review).

```
Traditional CCTV:  Camera -> Recording -> Human review -> Incident found -> Corrective action
This system:       Camera -> AI perception -> Behaviour understanding -> Risk detection -> Alert -> Intervention -> Learning
```

## Team ownership (per README / folder structure)

| Folder | Owner | Status |
|---|---|---|
| `computer_vision/` | CV/video intelligence | Phases 1-7 built and tested against 6 real videos; product-detection accuracy fix in progress (see `data/annotations/detection_findings.md`) |
| `backend/` | Backend | Empty placeholders only, not started |
| `frontend/` | Frontend | Empty placeholder (`package.json` only, 0 bytes), not started |
| `ai_assistant/` | AI assistant | Empty placeholders only, not started |
| `docs/` | Shared | This file + `api-contract.md` + `event-schema.md`, written by CV to unblock the others |

## Full pipeline (target)

```
                 WAREHOUSE VIDEO
                       |
                       v
                OpenCV Video IO
                       |
                       v
              YOLO Person Detection  +  Product Detection (YOLO-World, pending validation)
                       |
                       v
                 ByteTrack (person) / IoU tracker (product)
                       |
                       v
             Motion Feature Engine (velocity, acceleration, proximity, floor-proxy)
                       |
                       v
             Rule-Based Behaviour Detection (temporal windows)
                       |
                       v
                Risk Engine (config/behaviours.yaml)
                       |
                       v
                Event Generator (events.json / events.csv)
                       |
          -------------+-------------
          |             |             |
     Backend API    Incident clips   Annotated video
          |         (not built yet)
          v
    Frontend dashboard / AI assistant
```

## What's actually built vs. planned

See `computer_vision/README.md` for the authoritative, up-to-date phase-by-
phase status table - don't duplicate/maintain it here, it will go stale.
As of this writing: person detection/tracking and the behaviour-engine
*logic* are verified working; product detection has a known failure mode
on busy scenes (motion-blob approach) with a pretrained fix (YOLO-World)
built but not yet validated on real hardware with normal internet access.

## Key engineering decisions (and why)

- **No custom-trained detector for carton/mattress/pallet (yet).** COCO
  YOLO has no such classes (verified empirically). Rather than spend the
  hackathon's limited time annotating a training set, we tried a pretrained
  open-vocabulary detector (YOLO-World) first - "use pretrained models
  wherever possible" per the challenge brief. Custom training remains the
  fallback if YOLO-World underperforms (small dataset, 2-3 classes, very
  feasible in a few hours).
- **Rule-based behaviour detection, not a trained action-recognition
  model.** Given ~6 labeled clips (nowhere near enough for statistical
  threshold tuning or training a classifier), transparent, explainable
  rules over motion features are more defensible and easier to debug than
  a black-box model trained on too little data.
- **Never claim confirmed damage.** Every event's `damage_status` is
  `potential_damage_risk`. A bounding box cannot prove a product was
  physically damaged - only that a risky behaviour was observed. This is a
  hard requirement from the responsible-AI section of the brief.
- **Operator anonymity.** No facial recognition or identity linking is
  performed anywhere in the pipeline. Detected people are referred to by
  ephemeral track IDs only ("PERSON #3"), never named or re-identified
  across videos.
