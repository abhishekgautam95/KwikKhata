from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request

from database import KhataDB
from services.message_router import MessageRouter
from services.whatsapp_client import parse_incoming_messages, verify_webhook_token

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
db = KhataDB()
message_router = MessageRouter(db)


@router.get("/whatsapp")
async def verify_whatsapp_webhook(
    hub_mode: str = Query(alias="hub.mode"),
    hub_verify_token: str = Query(alias="hub.verify_token"),
    hub_challenge: str = Query(alias="hub.challenge"),
):
    challenge = verify_webhook_token(hub_mode, hub_verify_token, hub_challenge)
    if challenge is None:
        raise HTTPException(status_code=403, detail="verification failed")
    return int(challenge) if challenge.isdigit() else challenge


@router.post("/whatsapp")
async def receive_whatsapp_webhook(request: Request):
    payload = await request.json()
    messages = parse_incoming_messages(payload)
    routed = message_router.route(messages)
    return {"ok": True, "processed": len(routed)}
