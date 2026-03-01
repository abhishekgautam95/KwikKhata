from __future__ import annotations

import json
import urllib.parse
import urllib.request
from typing import Any

from config import settings
from models.message import IncomingMessage


def _auth_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.whatsapp_access_token}",
        "Content-Type": "application/json",
    }


def verify_webhook_token(mode: str, token: str, challenge: str) -> str | None:
    if mode != "subscribe":
        return None
    if token != settings.whatsapp_verify_token:
        return None
    return challenge


def parse_incoming_messages(payload: dict[str, Any]) -> list[IncomingMessage]:
    messages: list[IncomingMessage] = []
    entries = payload.get("entry") or []
    for entry in entries:
        changes = entry.get("changes") or []
        for change in changes:
            value = change.get("value") or {}
            message_rows = value.get("messages") or []
            for row in message_rows:
                mtype = row.get("type", "unknown")
                msg = IncomingMessage(
                    message_id=str(row.get("id", "")),
                    from_number=str(row.get("from", "")),
                    type=mtype if mtype in {"text", "audio", "image"} else "unknown",
                    timestamp=str(row.get("timestamp", "")),
                )
                if msg.type == "text":
                    msg.text = str((row.get("text") or {}).get("body", ""))
                elif msg.type == "audio":
                    audio = row.get("audio") or {}
                    msg.media_id = str(audio.get("id", ""))
                    msg.mime_type = str(audio.get("mime_type", ""))
                elif msg.type == "image":
                    image = row.get("image") or {}
                    msg.media_id = str(image.get("id", ""))
                    msg.mime_type = str(image.get("mime_type", ""))
                    msg.text = str(image.get("caption", ""))
                messages.append(msg)
    return messages


def send_text_message(to_number: str, body: str) -> dict[str, Any]:
    if not settings.whatsapp_phone_number_id or not settings.whatsapp_access_token:
        return {"ok": False, "error": "WHATSAPP credentials missing"}

    url = (
        f"{settings.whatsapp_api_base}/{settings.whatsapp_graph_version}/"
        f"{settings.whatsapp_phone_number_id}/messages"
    )
    payload = {"messaging_product": "whatsapp", "to": to_number, "type": "text", "text": {"body": body}}
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=_auth_headers(),
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return {"ok": True, "status": resp.getcode(), "body": resp.read().decode("utf-8")}
    except Exception as exc:  # pragma: no cover - network path
        return {"ok": False, "error": str(exc)}


def fetch_media_url(media_id: str) -> str | None:
    if not media_id:
        return None
    url = f"{settings.whatsapp_api_base}/{settings.whatsapp_graph_version}/{urllib.parse.quote(media_id)}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {settings.whatsapp_access_token}"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            return body.get("url")
    except Exception:  # pragma: no cover - network path
        return None


def download_media_bytes(media_url: str) -> bytes | None:
    if not media_url:
        return None
    req = urllib.request.Request(media_url, headers={"Authorization": f"Bearer {settings.whatsapp_access_token}"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.read()
    except Exception:  # pragma: no cover - network path
        return None
