from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from config import settings
from services.compliance_service import ComplianceStore

router = APIRouter(prefix="/compliance", tags=["compliance"])
store = ComplianceStore()


def _authorize(token: str) -> None:
    expected = settings.dashboard_token.strip()
    if expected and token.strip() != expected:
        raise HTTPException(status_code=403, detail="invalid compliance token")


class ConsentIn(BaseModel):
    subject_id: str = Field(min_length=1, max_length=120)
    channel: str = Field(default="whatsapp", min_length=1, max_length=40)
    consent: str = Field(default="granted", min_length=1, max_length=40)


@router.post("/consent")
async def record_consent(body: ConsentIn, x_compliance_token: str = Header(default="")):
    _authorize(x_compliance_token)
    store.append_event(
        event_type="consent",
        subject_id=body.subject_id.strip(),
        payload={"channel": body.channel.strip(), "consent": body.consent.strip()},
    )
    return {"ok": True}


@router.get("/export/{subject_id}")
async def export_subject(subject_id: str, x_compliance_token: str = Header(default="")):
    _authorize(x_compliance_token)
    rows = store.export_subject_events(subject_id.strip())
    return {"ok": True, "count": len(rows), "items": rows}


@router.delete("/subject/{subject_id}")
async def delete_subject(subject_id: str, x_compliance_token: str = Header(default="")):
    _authorize(x_compliance_token)
    removed = store.delete_subject_events(subject_id.strip())
    return {"ok": True, "removed": removed}
