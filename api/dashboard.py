from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, Query

from config import settings
from database import create_db
from services.dashboard_service import build_dashboard_summary

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
db = create_db()


@router.get("/summary")
async def dashboard_summary(
    trend_days: int = Query(default=14, ge=1, le=90),
    x_dashboard_token: str = Header(default=""),
):
    expected = settings.dashboard_token.strip()
    if expected and x_dashboard_token.strip() != expected:
        raise HTTPException(status_code=403, detail="invalid dashboard token")
    return {"ok": True, "data": build_dashboard_summary(db, trend_days=trend_days)}
