from __future__ import annotations

from dataclasses import dataclass

from .schemas import EventCreate, RiskLevel

BASE_SCORES = {
    "dropping": 75,
    "throwing": 80,
    "dragging": 50,
    "rough_handling": 65,
    "improper_stacking": 60,
    "unstable_stacking": 70,
    "outside_designated_area": 40,
    "strap_assisted_handling": 50,
    "stepping_on_carton": 65,
    "unsafe_loading_sequence": 65,
}


@dataclass(frozen=True)
class Assessment:
    score: int
    level: RiskLevel
    explanation: str
    base_score: int
    confidence_factor: int
    duration_factor: int
    repeat_factor: int


def assess(event: EventCreate, repeat_frequency: int) -> Assessment:
    duration = event.end_time - event.start_time
    base_score = BASE_SCORES[event.behaviour]
    confidence_factor = 8 if event.confidence >= 0.8 else 4 if event.confidence >= 0.6 else 0
    duration_factor = 7 if duration >= 5 else 4 if duration >= 2 else 0
    repeat_factor = min(repeat_frequency * 3, 10)
    score = min(100, base_score + confidence_factor + duration_factor + repeat_factor)
    level: RiskLevel = "CRITICAL" if score >= 80 else "HIGH" if score >= 60 else "MEDIUM" if score >= 30 else "LOW"
    if event.reported_risk:
        # The Computer Vision contract already assigns a configured level.
        # Keep it stable while placing the enriched numeric score in its range.
        level = event.reported_risk
        bounds = {"LOW": (0, 29), "MEDIUM": (30, 59), "HIGH": (60, 79), "CRITICAL": (80, 100)}
        lower, upper = bounds[level]
        score = min(upper, max(lower, score))
    explanation = (
        f"{event.reason} Risk score {score}/100 is based on {event.behaviour.replace('_', ' ')}, "
        f"{event.confidence:.0%} detection confidence, {duration:.2f} seconds duration"
        + (f", and {repeat_frequency} similar recent event(s) in this video" if repeat_frequency else "")
        + ". This indicates potential handling risk, not confirmed product damage."
    )
    return Assessment(score, level, explanation, base_score, confidence_factor, duration_factor, repeat_factor)
