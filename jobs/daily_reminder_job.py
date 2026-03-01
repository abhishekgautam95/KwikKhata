from __future__ import annotations

from database import KhataDB
from services.reminder_engine import run_daily_owner_summary


def run_daily_reminder_job() -> dict:
    db = KhataDB()
    return run_daily_owner_summary(db)
