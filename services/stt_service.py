from __future__ import annotations

import json
import uuid
import urllib.request

from config import settings


def transcribe_audio_bytes(audio_bytes: bytes, filename: str = "audio.ogg") -> str | None:
    """
    Transcribe audio using OpenAI audio transcription API.
    Returns plain text or None on failure.
    """
    if not audio_bytes:
        return None
    if not settings.openai_api_key:
        return None

    boundary = f"----KwikKhataBoundary{uuid.uuid4().hex}"
    parts: list[bytes] = []

    def add_field(name: str, value: str) -> None:
        parts.append(f"--{boundary}\r\n".encode())
        parts.append(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode())
        parts.append(f"{value}\r\n".encode())

    parts.append(f"--{boundary}\r\n".encode())
    parts.append(
        (
            'Content-Disposition: form-data; name="file"; filename="'
            + filename
            + '"\r\nContent-Type: application/octet-stream\r\n\r\n'
        ).encode()
    )
    parts.append(audio_bytes)
    parts.append(b"\r\n")
    add_field("model", settings.whisper_model)
    add_field("response_format", "json")
    parts.append(f"--{boundary}--\r\n".encode())
    body = b"".join(parts)

    req = urllib.request.Request(
        "https://api.openai.com/v1/audio/transcriptions",
        data=body,
        headers={
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
            return (payload.get("text") or "").strip() or None
    except Exception:  # pragma: no cover - network path
        return None
