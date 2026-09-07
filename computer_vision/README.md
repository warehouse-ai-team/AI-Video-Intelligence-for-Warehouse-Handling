# Warehouse AI Team Project

AI-powered video intelligence for warehouse loading/unloading — detects
risky handling behaviour (dropping, throwing, dragging, improper stacking,
stepping on cartons, etc.) from dock CCTV footage and generates structured,
evidence-backed alerts instead of relying on after-the-fact human review of
raw recordings.

## Team structure

| Folder | Responsibility | Status |
|---|---|---|
| `computer_vision/` | Video ingestion, detection, tracking, behaviour/risk detection, event generation | In progress — detection, tracking and Behaviour Intelligence modules implemented and under validation |
| `backend/` | API serving events/videos to frontend + assistant | Not started |
| `frontend/` | Dashboard UI | Not started |
| `ai_assistant/` | Conversational assistant over event data | Not started |
| `docs/` | Shared architecture & integration contract | `architecture.md`, `api-contract.md`, `event-schema.md` — written by the CV side to unblock the others, should be updated whoever builds on top |
| `data/sample_events/` | Real (but accuracy-unvalidated) sample event output for frontend/backend dev | See `data/sample_events/NOTE.md` before using |

## Start here

- Building the CV pipeline further? → `computer_vision/README.md`
- Working on Behaviour Intelligence? → `computer_vision/src/behaviour.py` and `computer_vision/config/behaviours.yaml`
- Evaluating behaviour detection? → `computer_vision/src/evaluation.py`
- Running behaviour tests? → `computer_vision/tests/test_behaviour_synthetic.py`
- Building the backend or frontend? → `docs/api-contract.md` and `docs/event-schema.md`
- Want the honest "what's actually verified to work" record? → `computer_vision/data/annotations/detection_findings.md`

## Behaviour Intelligence

The Behaviour Intelligence module analyses object tracking data and applies
rule-based state-transition logic to identify risky warehouse handling actions.

Currently supported behaviours include:

- Dropping
- Throwing
- Dragging
- Rough handling
- Improper stacking
- Unstable stacking
- Outside designated area
- Strap-assisted handling
- Stepping on cartons
- Unsafe loading sequence

Behaviour thresholds and detection parameters are maintained in
`computer_vision/config/behaviours.yaml`.

Synthetic tests and evaluation utilities are provided to validate behaviour
rules and compare detected events against available ground-truth annotations.
Behaviour detection accuracy still requires validation on the final tracking
outputs from the Computer Vision pipeline.

## Responsible AI

This system flags **potential risk**, never confirmed damage — a camera
cannot verify physical product damage, only risky handling behaviour. It does
not identify workers by name or face; detected people are referred to by
ephemeral track IDs only. See `docs/architecture.md` for the full list of
engineering decisions driven by this.