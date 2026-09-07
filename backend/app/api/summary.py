from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException

from ..config import SAMPLE_EVENTS_PATH
from ..database import connection
from ..schemas import EventCreate, Summary
from .events import create_event

router = APIRouter(tags=["summary"])


@router.get("/summary", response_model=Summary)
def get_summary() -> Summary:
    with connection() as db:
        counts = {level: db.execute("SELECT COUNT(*) FROM events WHERE risk_level = ?", (level,)).fetchone()[0] for level in ("LOW", "MEDIUM", "HIGH", "CRITICAL")}
        behaviour = db.execute("SELECT behaviour FROM events GROUP BY behaviour ORDER BY COUNT(*) DESC, behaviour LIMIT 1").fetchone()
        video = db.execute("SELECT video_id FROM events GROUP BY video_id ORDER BY COUNT(*) DESC, video_id LIMIT 1").fetchone()
    return Summary(total_events=sum(counts.values()), low_risk_events=counts["LOW"], medium_risk_events=counts["MEDIUM"], high_risk_events=counts["HIGH"], critical_risk_events=counts["CRITICAL"], most_common_behaviour=behaviour[0] if behaviour else None, busiest_risky_video=video[0] if video else None)


@router.post("/seed/sample")
def seed_sample_events() -> dict[str, int]:
    if not SAMPLE_EVENTS_PATH.exists():
        raise HTTPException(status_code=404, detail="Sample events file not found")
    created = skipped = 0
    for item in json.loads(SAMPLE_EVENTS_PATH.read_text(encoding="utf-8")):
        try:
            create_event(EventCreate.model_validate(item))
            created += 1
        except HTTPException as exc:
            if exc.status_code != 409:
                raise
            skipped += 1
    return {"created": created, "skipped_existing": skipped}
