from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request

from config import settings
from database import create_db
from services.rate_limiter import InMemorySlidingWindowRateLimiter
from services.security_utils import verify_hmac_signature
from services.message_router import MessageRouter
from services.whatsapp_client import parse_incoming_messages, verify_webhook_token

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
db = create_db()
message_router = MessageRouter(db)
webhook_limiter = InMemorySlidingWindowRateLimiter(
    limit=settings.webhook_rate_limit_per_minute,
    window_seconds=settings.webhook_rate_limit_window_seconds,
)


def _client_key(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "").strip()
    if forwarded:
        return forwarded.split(",")[0].strip()
    client = request.client
    if client and client.host:
        return client.host
    return "unknown"


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
    limit_result = webhook_limiter.check(_client_key(request))
    if not limit_result.allowed:
        raise HTTPException(
            status_code=429,
            detail=f"rate limit exceeded; retry in {limit_result.retry_after_seconds}s",
            headers={"Retry-After": str(limit_result.retry_after_seconds)},
        )

    body = await request.body()
    max_bytes = max(1, int(settings.webhook_max_payload_kb)) * 1024
    if len(body) > max_bytes:
        raise HTTPException(status_code=413, detail="payload too large")
    signature = request.headers.get("x-kwikkhata-signature", "")
    if not verify_hmac_signature(body, signature, settings.webhook_signature_secret):
        raise HTTPException(status_code=403, detail="invalid webhook signature")

    payload = await request.json()
    messages = parse_incoming_messages(payload)
    routed = message_router.route(messages)
    return {"ok": True, "processed": len(routed)}
