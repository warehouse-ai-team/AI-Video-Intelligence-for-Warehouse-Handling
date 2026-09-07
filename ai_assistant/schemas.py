from __future__ import annotations
from typing import Optional, Literal
from pydantic import BaseModel

RiskLevel = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]

Behaviour = Literal[
    "dropping", "throwing", "dragging", "rough_handling", "improper_stacking",
    "unstable_stacking", "outside_designated_area", "strap_assisted_handling",
    "stepping_on_carton", "unsafe_loading_sequence",
]


class WarehouseEvent(BaseModel):
    event_id: str
    video_id: str
    start_frame: Optional[int] = None
    end_frame: Optional[int] = None
    start_time: float
    end_time: float
    behaviour: Behaviour
    confidence: float
    evidence: Optional[str] = None
    reason: str
    damage_status: Literal["potential_damage_risk"]
    risk_level: RiskLevel
    risk_score: int
    risk_explanation: str
    created_at: str


class RiskFactors(BaseModel):
    behaviour: Behaviour
    duration_seconds: float
    repeat_frequency: int
    base_score: int
    confidence_factor: int
    duration_factor: int
    repeat_factor: int


class RiskScore(BaseModel):
    event_id: str
    score: int
    level: RiskLevel
    factors: RiskFactors


class Summary(BaseModel):
    total_events: int
    low_risk_events: int
    medium_risk_events: int
    high_risk_events: int
    critical_risk_events: int
    most_common_behaviour: Optional[str] = None
    busiest_risky_video: Optional[str] = None


# --- Chat endpoint contract (unchanged from before) ---

class ChatRequest(BaseModel):
    question: str
    selected_event_id: Optional[str] = None


class ChatResponse(BaseModel):
    answer: str
    tools_used: list[str] = []