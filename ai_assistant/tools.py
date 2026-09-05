from __future__ import annotations
import httpx
from typing import Any

BACKEND_URL = "http://localhost:8000"  # override via config in real deployment


class BackendError(Exception):
    pass


def _get(path: str, params: dict | None = None) -> Any:
    try:
        resp = httpx.get(f"{BACKEND_URL}{path}", params=params, timeout=10.0)
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPError as exc:
        raise BackendError(f"Backend request to {path} failed: {exc}") from exc


# --- Tool executors -------------------------------------------------

def get_events(bay: str | None = None, risk_level: str | None = None,
                behaviour_type: str | None = None) -> dict:
    params = {k: v for k, v in {
        "bay": bay, "risk_level": risk_level, "behaviour_type": behaviour_type,
    }.items() if v}
    return {"events": _get("/events", params)}


def get_event_by_id(event_id: str) -> dict:
    return _get(f"/events/{event_id}")


def get_risk_scores(event_id: str | None = None) -> dict:
    params = {"event_id": event_id} if event_id else None
    return {"risk_scores": _get("/risk-scores", params)}


def get_busiest_bay() -> dict:
    return _get("/supervisor/busiest-bay")


def get_most_common_behaviour() -> dict:
    return _get("/supervisor/most-common-behaviour")


def compare_morning_afternoon(date: str | None = None) -> dict:
    params = {"date": date} if date else None
    return _get("/supervisor/morning-vs-afternoon", params)


# --- Tool schemas for the Claude API ---------------------------------

TOOL_DEFINITIONS = [
    {
        "name": "get_events",
        "description": (
            "Fetch warehouse events, optionally filtered by bay, risk level, "
            "or behaviour type. Use this for questions about what happened, "
            "how often, or which incidents match certain criteria."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "bay": {"type": "string", "description": "Bay name, e.g. 'Bay 3'"},
                "risk_level": {
                    "type": "string",
                    "enum": ["low", "medium", "high", "critical"],
                },
                "behaviour_type": {
                    "type": "string",
                    "enum": [
                        "drop", "drag", "rough_handling", "unstable_stacking",
                        "outside_designated_area", "no_equipment_used",
                        "incorrect_pallet_placement", "push_or_throw",
                        "unsafe_sequence", "overloading",
                    ],
                },
            },
        },
    },
    {
        "name": "get_event_by_id",
        "description": "Fetch a single event's full record by its event_id.",
        "input_schema": {
            "type": "object",
            "properties": {"event_id": {"type": "string"}},
            "required": ["event_id"],
        },
    },
    {
        "name": "get_risk_scores",
        "description": "Fetch risk score details, optionally for one event_id.",
        "input_schema": {
            "type": "object",
            "properties": {"event_id": {"type": "string"}},
        },
    },
    {
        "name": "get_busiest_bay",
        "description": "Get the bay with the most recorded incidents.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_most_common_behaviour",
        "description": "Get the most frequently detected behaviour type overall.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "compare_morning_afternoon",
        "description": "Compare incident counts between morning and afternoon for a given date.",
        "input_schema": {
            "type": "object",
            "properties": {"date": {"type": "string", "description": "YYYY-MM-DD"}},
        },
    },
]

TOOL_EXECUTORS = {
    "get_events": get_events,
    "get_event_by_id": get_event_by_id,
    "get_risk_scores": get_risk_scores,
    "get_busiest_bay": get_busiest_bay,
    "get_most_common_behaviour": get_most_common_behaviour,
    "compare_morning_afternoon": compare_morning_afternoon,
}