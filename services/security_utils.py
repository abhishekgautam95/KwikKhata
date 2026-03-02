from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any

from config import settings

SENSITIVE_KEYS = {
    "authorization",
    "access_token",
    "token",
    "phone",
    "phone_number",
    "from",
    "to",
    "customer_phonebook",
}


def mask_phone(number: str) -> str:
    digits = "".join(ch for ch in str(number) if ch.isdigit())
    if len(digits) <= 4:
        return "*" * len(digits)
    return f"{'*' * (len(digits) - 4)}{digits[-4:]}"


def hash_identifier(value: str) -> str:
    text = str(value).strip()
    if not text:
        return ""
    salt = settings.pii_hash_salt or "kwikkhata-default-salt"
    digest = hmac.new(salt.encode("utf-8"), text.encode("utf-8"), hashlib.sha256).hexdigest()
    return digest[:16]


def redact_sensitive(value: Any) -> Any:
    if isinstance(value, dict):
        cleaned: dict[str, Any] = {}
        for key, raw in value.items():
            key_l = str(key).strip().lower()
            if key_l in SENSITIVE_KEYS:
                cleaned[key] = "***redacted***"
            else:
                cleaned[key] = redact_sensitive(raw)
        return cleaned
    if isinstance(value, list):
        return [redact_sensitive(v) for v in value]
    if isinstance(value, str) and value.startswith("Bearer "):
        return "Bearer ***redacted***"
    return value


def safe_json(value: Any) -> str:
    return json.dumps(redact_sensitive(value), ensure_ascii=True, separators=(",", ":"))
