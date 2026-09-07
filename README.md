# Warehouse AI Team Project

AI-powered video intelligence for warehouse loading/unloading — detects
risky handling behaviour (dropping, throwing, dragging, improper stacking,
stepping on cartons, etc.) from dock CCTV footage and generates structured,
evidence-backed alerts instead of relying on after-the-fact human review of
raw recordings.

## Team structure

| Folder | Responsibility | Status |
|---|---|---|
| `computer_vision/` | Video ingestion, detection, tracking, behaviour/risk detection, event generation | In progress — see `computer_vision/README.md` for the real phase-by-phase status |
| `backend/` | API serving events/videos to frontend + assistant | Not started |
| `frontend/` | Dashboard UI | Not started |
| `ai_assistant/` | Conversational assistant over event data | Not started |
| `docs/` | Shared architecture & integration contract | `architecture.md`, `api-contract.md`, `event-schema.md` — written by the CV side to unblock the others, should be updated by whoever builds on top |
| `data/sample_events/` | Real (but accuracy-unvalidated) sample event output for frontend/backend dev | See `data/sample_events/NOTE.md` before using |

## Start here

- Building the CV pipeline further? → `computer_vision/README.md`
- Building the backend or frontend? → `docs/api-contract.md` and `docs/event-schema.md`
- Want the honest "what's actually verified to work" record? → `computer_vision/data/annotations/detection_findings.md`

## Backend (Member 3)

The FastAPI backend receives Computer Vision events, calculates explainable
potential-risk scores, and stores events plus score factors in SQLite. See
`docs/backend.md` for setup, endpoints, and local demo commands.

## Responsible AI

This system flags **potential risk**, never confirmed damage — a camera
cannot verify physical product damage, only risky handling behaviour. It
does not identify workers by name or face; detected people are referred to
by ephemeral track IDs only. See `docs/architecture.md` for the full list
of engineering decisions driven by this.
