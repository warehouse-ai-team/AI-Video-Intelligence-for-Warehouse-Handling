from __future__ import annotations

import os
from pathlib import Path

BACKEND_DIRECTORY = Path(__file__).resolve().parents[1]
PROJECT_DIRECTORY = BACKEND_DIRECTORY.parent
DATABASE_PATH = Path(os.getenv("WAREHOUSE_DATABASE_PATH", BACKEND_DIRECTORY / "warehouse.db"))
SAMPLE_EVENTS_PATH = PROJECT_DIRECTORY / "data" / "sample_events" / "events.json"
