from __future__ import annotations
import os
from collections import Counter
from datetime import datetime
import httpx

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")


class BackendError(Exception):
    pass


def _get(path: str, params: dict | None = None):
    try:
        resp = httpx.get(f"{BACKEND_URL}{path}", params=params, timeout=10.0)
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPError as exc:
        raise BackendError(f"Backend request to {path} failed: {exc}") from exc


# --- Tool executors, matching backend/app/api/events.py + summary.py exactly ---

def get_events(video_id: str | None = None, risk_level: str | None = None,
                behaviour: str | None = None) -> dict:
    params = {k: v for k, v in {
        "video_id": video_id, "risk_level": risk_level, "behaviour": behaviour,
    }.items() if v}
    return {"events": _get("/events", params)}


def get_event_by_id(event_id: str) -> dict:
    return _get(f"/events/{event_id}")


def get_risk_scores(event_id: str | None = None) -> dict:
    params = {"event_id": event_id} if event_id else None
    return {"risk_scores": _get("/risk-scores", params)}


def get_summary() -> dict:
    # Covers "most common behaviour" and "busiest video" — the backend has
    # one aggregate endpoint rather than separate supervisor-query routes.
    return _get("/summary")


def compare_time_of_day(date: str | None = None) -> dict:
    """
    No dedicated backend endpoint for this — compute it from raw events
    since the backend only exposes created_at, not a morning/afternoon
    aggregate. Buckets by the hour of created_at (UTC).
    """
    events = _get("/events")
    morning, afternoon = 0, 0
    for e in events:
        try:
            ts = datetime.fromisoformat(e["created_at"].replace("Z", "+00:00"))
        except (KeyError, ValueError):
            continue
        if date and ts.strftime("%Y-%m-%d") != date:
            continue
        if ts.hour < 12:
            morning += 1
        else:
            afternoon += 1
    return {"morning_count": morning, "afternoon_count": afternoon, "note": (
        "Computed from event created_at timestamps; no dedicated backend "
        "endpoint exists for this comparison."
    )}


def get_risk_level_breakdown() -> dict:
    events = _get("/events")
    counts = Counter(e["risk_level"] for e in events)
    return {"breakdown": dict(counts), "total": len(events)}


# --- Tool schemas for the Claude API ---

TOOL_DEFINITIONS = [
    {
        "name": "get_events",
        "description": (
            "Fetch warehouse events, optionally filtered by video_id, risk_level, "
            "or behaviour. Use this for questions about what happened, how often, "
            "or which incidents match certain criteria."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "video_id": {"type": "string", "description": "e.g. 'V001'"},
                "risk_level": {
                    "type": "string",
                    "enum": ["LOW", "MEDIUM", "HIGH", "CRITICAL"],
                },
                "behaviour": {
                    "type": "string",
                    "enum": [
                        "dropping", "throwing", "dragging", "rough_handling",
                        "improper_stacking", "unstable_stacking",
                        "outside_designated_area", "strap_assisted_handling",
                        "stepping_on_carton", "unsafe_loading_sequence",
                    ],
                },
            },
        },
    },
    {
        "name": "get_event_by_id",
        "description": "Fetch a single event's full record, including its risk_explanation and reason, by event_id.",
        "input_schema": {
            "type": "object",
            "properties": {"event_id": {"type": "string"}},
            "required": ["event_id"],
        },
    },
    {
        "name": "get_risk_scores",
        "description": "Fetch the explainable risk-scoring factors (base_score, confidence_factor, duration_factor, repeat_factor) for events, optionally filtered to one event_id.",
        "input_schema": {
            "type": "object",
            "properties": {"event_id": {"type": "string"}},
        },
    },
    {
        "name": "get_summary",
        "description": (
            "Get aggregate dashboard totals: counts per risk level, the most "
            "common behaviour overall, and the busiest video by event count."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "compare_time_of_day",
        "description": "Compare how many events were recorded in the morning vs afternoon, optionally for a specific date (YYYY-MM-DD).",
        "input_schema": {
            "type": "object",
            "properties": {"date": {"type": "string", "description": "YYYY-MM-DD"}},
        },
    },
    {
        "name": "get_risk_level_breakdown",
        "description": "Get a count of events per risk level (LOW/MEDIUM/HIGH/CRITICAL) across all videos.",
        "input_schema": {"type": "object", "properties": {}},
    },
]

TOOL_EXECUTORS = {
    "get_events": get_events,
    "get_event_by_id": get_event_by_id,
    "get_risk_scores": get_risk_scores,
    "get_summary": get_summary,
    "compare_time_of_day": compare_time_of_day,
    "get_risk_level_breakdown": get_risk_level_breakdown,
}