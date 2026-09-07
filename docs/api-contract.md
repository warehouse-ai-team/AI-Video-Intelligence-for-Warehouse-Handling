# API Contract

Status: **`backend/app/` is currently empty (0-byte placeholder files) — no
API exists yet.** This doc specifies what the Computer Vision module can
supply and a suggested minimal contract, so whoever builds the backend
doesn't have to reverse-engineer it from code.

## What the CV module can supply today

1. **Event records** — see `docs/event-schema.md` for the full field
   reference. Available as static files after running the pipeline:
   - `computer_vision/outputs/events/events.json`
   - `computer_vision/outputs/events/events.csv`
2. **Tracking data** (lower-level, probably not needed by frontend/assistant
   directly) — `computer_vision/outputs/tracking/<video>_tracking.csv` and
   `<video>_features.csv` per processed video.
3. **Annotated videos** — `computer_vision/outputs/annotated_videos/<video>_tracked.mp4`,
   bounding boxes + track IDs burned in. No behaviour/risk overlay yet
   (planned, not built - see `computer_vision/README.md`).
4. **Ground truth** — `computer_vision/data/annotations/ground_truth.csv`,
   manually verified timestamps/behaviours for the 6 sample videos. Useful
   for a "known good" demo dataset while the live pipeline is being
   validated.

## Suggested minimal backend endpoints

Not binding — whoever builds `backend/app/main.py` should adjust to fit
their framework, but keep the response shapes matching `event-schema.md`
so the frontend doesn't need per-consumer translation logic.

```
GET /videos
  -> list of {video_id, filename, duration_sec, fps}
     (source: computer_vision/data/annotations/video_audit_report.csv)

GET /videos/{video_id}/events
  -> array of event records (see event-schema.md), filtered to that video_id

GET /events?risk_level=HIGH
  -> array of event records across all videos, optionally filtered

GET /videos/{video_id}/annotated-video
  -> streams/serves the corresponding *_tracked.mp4

GET /events/{event_id}/clip
  -> streams/serves the incident clip (NOT YET AVAILABLE - clips.py not built)
```

## Data flow (current, honest state)

```
6 uploaded videos
    -> computer_vision/src/run_tracking_demo.py   (person+product detection/tracking)
    -> computer_vision/src/features.py            (motion features)
    -> computer_vision/src/behaviour.py            (rule-based behaviour detection)
    -> computer_vision/src/events.py               (JSON/CSV event records)
    -> outputs/events/events.json, events.csv
    -> [backend - NOT BUILT] serves these to frontend/assistant
    -> [frontend - NOT BUILT] displays events, videos, risk dashboard
    -> [ai_assistant - NOT BUILT] answers questions using event records as context
```

There is currently no live/automated trigger from "new video uploaded" to
"events generated" — each stage is run manually via CLI. Building that
orchestration (e.g. a watch-folder + queue, or a simple "process on
upload" endpoint) is backend/infra work, not yet scoped to anyone.

## Environment variables / config

Nothing sensitive yet (no API keys, no DB). If the backend adds a database
or third-party service, document required env vars here and add a
`.env.example` (currently `.gitignore` excludes `.env` but expects
`.env.example` to exist and be committed — it doesn't exist yet either).
