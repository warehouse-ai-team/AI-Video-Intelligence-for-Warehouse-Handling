# Backend (Member 3)

The FastAPI backend receives the stable Computer Vision event schema from
`docs/event-schema.md`, calculates a transparent risk score, and stores the
result in SQLite. It preserves the original fields and adds `risk_score`,
`risk_explanation`, and `created_at`.

Member 2's raw detector JSON is accepted directly: `risk` is accepted as an
alias for the shared risk level, `start_frame` and `end_frame` are stored,
and a missing `event_id` is generated automatically. The raw detector does
not currently include `video_id`, so the API stores `UNKNOWN` until that
field is supplied by the pipeline.

Risk scoring is rule based: behaviour type, confidence, event duration, and
the count of similar events in the preceding 60 seconds of the same video.
When Computer Vision already supplies a configured risk level, the backend
preserves that shared value and calibrates the numeric score to its range.
Every event remains `potential_damage_risk`; the system never confirms
physical product damage from video alone.

## Run

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
uvicorn backend.app.main:app --reload
```

Open `http://localhost:8000/docs` for interactive API documentation.

## Endpoints

| Endpoint | Purpose |
| --- | --- |
| `GET /health` | Confirms the service is running |
| `POST /events` | Saves one Computer Vision event and calculates risk |
| `GET /events` | Lists events; filters: `video_id`, `risk_level`, `behaviour` |
| `GET /events/{event_id}` | Gets a single event |
| `GET /risk-scores` | Gets explainable scoring factors |
| `GET /summary` | Gets dashboard totals and trends |
| `POST /seed/sample` | Imports the supplied sample pipeline events |

## Demo commands

```powershell
Invoke-RestMethod -Method Post http://localhost:8000/seed/sample
Invoke-RestMethod http://localhost:8000/events
Invoke-RestMethod http://localhost:8000/summary
```
