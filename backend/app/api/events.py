from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from ..database import connection, row_to_event
from ..risk_engine import assess
from ..schemas import EventCreate, RiskScore, WarehouseEvent

router = APIRouter(tags=["events"])


def _repeat_frequency(db, event: EventCreate) -> int:
    return db.execute(
        """SELECT COUNT(*) FROM events WHERE video_id = ? AND behaviour = ?
           AND start_time >= ? AND start_time < ?""",
        (event.video_id, event.behaviour, max(0, event.start_time - 60), event.start_time),
    ).fetchone()[0]


@router.post("/events", response_model=WarehouseEvent, status_code=status.HTTP_201_CREATED)
def create_event(event: EventCreate) -> WarehouseEvent:
    with connection() as db:
        if db.execute("SELECT 1 FROM events WHERE event_id = ?", (event.event_id,)).fetchone():
            raise HTTPException(status_code=409, detail=f"Event {event.event_id} already exists")
        repeats = _repeat_frequency(db, event)
        result = assess(event, repeats)
        db.execute(
            """INSERT INTO events (event_id, video_id, start_frame, end_frame, start_time, end_time, behaviour, risk_level, confidence,
               evidence, reason, damage_status, risk_score, risk_explanation)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (event.event_id, event.video_id, event.start_frame, event.end_frame, event.start_time, event.end_time,
             event.behaviour, result.level, event.confidence, event.evidence, event.reason, event.damage_status,
             result.score, result.explanation),
        )
        db.execute(
            """INSERT INTO risk_scores (event_id, base_score, confidence_factor, duration_factor, repeat_factor,
               final_score, risk_level, repeat_frequency) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (event.event_id, result.base_score, result.confidence_factor, result.duration_factor,
             result.repeat_factor, result.score, result.level, repeats),
        )
        row = db.execute("SELECT * FROM events WHERE event_id = ?", (event.event_id,)).fetchone()
    return WarehouseEvent.model_validate(row_to_event(row))


@router.get("/events", response_model=list[WarehouseEvent])
def list_events(video_id: str | None = None, risk_level: str | None = None, behaviour: str | None = None) -> list[WarehouseEvent]:
    conditions, values = [], []
    for field, value in (("video_id", video_id), ("risk_level", risk_level), ("behaviour", behaviour)):
        if value:
            conditions.append(f"{field} = ?")
            values.append(value)
    where = f" WHERE {' AND '.join(conditions)}" if conditions else ""
    with connection() as db:
        rows = db.execute(f"SELECT * FROM events{where} ORDER BY video_id, start_time", values).fetchall()
    return [WarehouseEvent.model_validate(row_to_event(row)) for row in rows]


@router.get("/events/{event_id}", response_model=WarehouseEvent)
def get_event(event_id: str) -> WarehouseEvent:
    with connection() as db:
        row = db.execute("SELECT * FROM events WHERE event_id = ?", (event_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return WarehouseEvent.model_validate(row_to_event(row))


@router.get("/risk-scores", response_model=list[RiskScore])
def list_risk_scores(event_id: str | None = None) -> list[RiskScore]:
    query = """SELECT scores.*, events.behaviour, events.start_time, events.end_time
               FROM risk_scores scores JOIN events ON events.event_id = scores.event_id"""
    params: list[str] = []
    if event_id:
        query += " WHERE scores.event_id = ?"
        params.append(event_id)
    with connection() as db:
        rows = db.execute(query + " ORDER BY scores.created_at DESC", params).fetchall()
    return [RiskScore.model_validate({
        "event_id": row["event_id"], "score": row["final_score"], "level": row["risk_level"],
        "factors": {"behaviour": row["behaviour"], "duration_seconds": row["end_time"] - row["start_time"],
                    "repeat_frequency": row["repeat_frequency"], "base_score": row["base_score"],
                    "confidence_factor": row["confidence_factor"], "duration_factor": row["duration_factor"],
                    "repeat_factor": row["repeat_factor"]},
    }) for row in rows]
