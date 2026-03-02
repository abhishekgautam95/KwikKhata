from __future__ import annotations

import logging
from time import perf_counter

from fastapi import FastAPI
from starlette.requests import Request
from starlette.responses import Response

from api.compliance import router as compliance_router
from api.dashboard import router as dashboard_router
from api.ops import METRICS, router as ops_router
from api.public_v1 import router as public_v1_router
from api.whatsapp_webhook import router as whatsapp_router
from config import settings
from jobs.daily_reminder_job import run_daily_reminder_job

LOGGER = logging.getLogger("kwikkhata.api")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

app = FastAPI(title="KwikKhata Agent API", version="0.3.0")
app.include_router(whatsapp_router)
app.include_router(dashboard_router)
app.include_router(public_v1_router)
app.include_router(compliance_router)
app.include_router(ops_router)


@app.middleware("http")
async def request_metrics_middleware(request: Request, call_next):
    start = perf_counter()
    response: Response = await call_next(request)
    latency_ms = (perf_counter() - start) * 1000
    METRICS.record(
        path=request.url.path,
        method=request.method,
        status_code=response.status_code,
        latency_ms=latency_ms,
    )
    return response


@app.get("/health")
def health() -> dict:
    return {"ok": True, "env": settings.app_env, "data_backend": settings.data_backend}


@app.on_event("startup")
def startup_scheduler() -> None:
    """
    Daily reminder scheduler.
    If APScheduler is not installed, app still runs without scheduled job.
    """
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger
    except Exception:
        LOGGER.warning("APScheduler not installed; skipping reminder scheduler startup.")
        return

    try:
        hour, minute = settings.reminder_run_time.split(":", 1)
        trigger = CronTrigger(hour=int(hour), minute=int(minute))
    except Exception:
        trigger = CronTrigger(hour=10, minute=0)

    scheduler = BackgroundScheduler()
    scheduler.add_job(run_daily_reminder_job, trigger=trigger, id="daily-reminder", replace_existing=True)
    scheduler.start()
    app.state.scheduler = scheduler
    LOGGER.info("Reminder scheduler started at %s", settings.reminder_run_time)


@app.on_event("shutdown")
def stop_scheduler() -> None:
    scheduler = getattr(app.state, "scheduler", None)
    if scheduler:
        scheduler.shutdown(wait=False)
