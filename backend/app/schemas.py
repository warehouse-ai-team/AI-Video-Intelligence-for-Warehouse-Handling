from __future__ import annotations

from typing import Literal
from uuid import uuid4

from pydantic import AliasChoices, BaseModel, Field, model_validator

RiskLevel = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
DamageStatus = Literal["potential_damage_risk"]
Behaviour = Literal[
    "dropping", "throwing", "dragging", "rough_handling", "improper_stacking",
    "unstable_stacking", "outside_designated_area", "strap_assisted_handling",
    "stepping_on_carton", "unsafe_loading_sequence",
]


class EventCreate(BaseModel):
    event_id: str = Field(default_factory=lambda: f"EVT_{uuid4().hex[:12].upper()}")
    video_id: str = "UNKNOWN"
    start_frame: int | None = Field(default=None, ge=0)
    end_frame: int | None = Field(default=None, ge=0)
    start_time: float = Field(ge=0)
    end_time: float = Field(ge=0)
    behaviour: Behaviour
    # Accept both the shared field and Member 2's raw `risk` field.
    reported_risk: RiskLevel | None = Field(
        default=None, validation_alias=AliasChoices("risk", "risk_level"), exclude=True
    )
    confidence: float = Field(ge=0, le=1)
    evidence: str | None = None
    reason: str = Field(min_length=1)
    damage_status: DamageStatus = "potential_damage_risk"

    @model_validator(mode="after")
    def end_time_must_follow_start_time(self) -> "EventCreate":
        if self.end_time < self.start_time:
            raise ValueError("end_time must be greater than or equal to start_time")
        return self


class WarehouseEvent(EventCreate):
    risk_level: RiskLevel
    risk_score: int = Field(ge=0, le=100)
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
    most_common_behaviour: str | None
    busiest_risky_video: str | None
