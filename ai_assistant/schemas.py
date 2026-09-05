from __future__ import annotations
from typing import Optional, Literal
from pydantic import BaseModel

RiskLevel = Literal["low", "medium", "high", "critical"]

BehaviourType = Literal[
    "drop",
    "drag",
    "rough_handling",
    "unstable_stacking",
    "outside_designated_area",
    "no_equipment_used",
    "incorrect_pallet_placement",
    "push_or_throw",
    "unsafe_sequence",
    "overloading",
]


class BoundingBox(BaseModel):
    x: float
    y: float
    width: float
    height: float


class WarehouseEvent(BaseModel):
    event_id: str
    video_id: str
    track_id: str
    behaviour_type: BehaviourType
    confidence: float
    timestamp: str
    video_time_seconds: float
    bbox: BoundingBox
    bay: Optional[str] = None
    risk_level: RiskLevel
    risk_explanation: Optional[str] = None


class RiskScore(BaseModel):
    event_id: str
    score: float
    level: RiskLevel


# --- Chat endpoint contract (what the frontend's ChatPanel will call) ---

class ChatRequest(BaseModel):
    question: str
    selected_event_id: Optional[str] = None


class ChatResponse(BaseModel):
    answer: str
    # Names of backend tools the assistant actually called, so the
    # frontend/tests can verify grounding rather than trusting free text.
    tools_used: list[str] = []