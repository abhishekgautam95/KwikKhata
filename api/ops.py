from __future__ import annotations

from fastapi import APIRouter, Query

from config import settings
from services.monitoring import InMemoryMetrics

router = APIRouter(prefix="/ops", tags=["ops"])
METRICS = InMemoryMetrics(window_size=settings.metrics_window_size)


@router.get("/metrics")
async def metrics():
    return {"ok": True, "data": METRICS.snapshot()}


@router.get("/slo")
async def slo(
    max_error_rate: float = Query(default=0.01, ge=0.0, le=1.0),
    max_p95_ms: float = Query(default=800, ge=1.0, le=10_000.0),
):
    return {"ok": True, "data": METRICS.slo(max_error_rate=max_error_rate, max_p95_ms=max_p95_ms)}
