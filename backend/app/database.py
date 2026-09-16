from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from typing import Iterator

from .config import DATABASE_PATH


@contextmanager
def connection() -> Iterator[sqlite3.Connection]:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DATABASE_PATH)
    db.row_factory = sqlite3.Row
    try:
        yield db
        db.commit()
    finally:
        db.close()


def initialize_database() -> None:
    with connection() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS events (
                event_id TEXT PRIMARY KEY,
                video_id TEXT NOT NULL,
                start_frame INTEGER,
                end_frame INTEGER,
                start_time REAL NOT NULL,
                end_time REAL NOT NULL,
                behaviour TEXT NOT NULL,
                risk_level TEXT NOT NULL,
                confidence REAL NOT NULL,
                evidence TEXT,
                reason TEXT NOT NULL,
                damage_status TEXT NOT NULL,
                risk_score INTEGER NOT NULL,
                risk_explanation TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_events_filters
                ON events(video_id, behaviour, risk_level, start_time);
            CREATE TABLE IF NOT EXISTS risk_scores (
                event_id TEXT PRIMARY KEY REFERENCES events(event_id),
                base_score INTEGER NOT NULL,
                confidence_factor INTEGER NOT NULL,
                duration_factor INTEGER NOT NULL,
                repeat_factor INTEGER NOT NULL,
                final_score INTEGER NOT NULL,
                risk_level TEXT NOT NULL,
                repeat_frequency INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        columns = {row["name"] for row in db.execute("PRAGMA table_info(events)")}
        for name in ("start_frame", "end_frame"):
            if name not in columns:
                db.execute(f"ALTER TABLE events ADD COLUMN {name} INTEGER")


def row_to_event(row: sqlite3.Row) -> dict:
    return dict(row)
