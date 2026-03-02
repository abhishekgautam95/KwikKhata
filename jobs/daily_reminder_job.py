from __future__ import annotations

from database import create_db
from services.reminder_engine import run_daily_owner_summary


def run_daily_reminder_job() -> dict:
    db = create_db()
    return run_daily_owner_summary(db)
