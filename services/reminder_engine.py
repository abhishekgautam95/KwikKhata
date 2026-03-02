from __future__ import annotations

import json
import os
import base64
from dataclasses import dataclass

from config import settings
from database import KhataDB
from services.whatsapp_client import send_text_message


@dataclass
class ReminderCandidate:
    name: str
    balance: float
    pending_days: int
    score: float


def _load_phonebook() -> dict[str, str]:
    """
    CUSTOMER_PHONEBOOK JSON format:
    {"Raju":"+91999...", "Aditya":"+91888..."}
    """
    raw = os.getenv("CUSTOMER_PHONEBOOK", "").strip()
    encoded = os.getenv("CUSTOMER_PHONEBOOK_B64", "").strip()
    if encoded and not raw:
        try:
            raw = base64.b64decode(encoded.encode("utf-8")).decode("utf-8")
        except Exception:
            raw = ""
    if not raw:
        return {}
    try:
        payload = json.loads(raw)
        if isinstance(payload, dict):
            normalized: dict[str, str] = {}
            for k, v in payload.items():
                name = str(k).strip().title()
                number = _sanitize_phone_number(str(v))
                if name and number:
                    normalized[name] = number
            return normalized
    except Exception:
        return {}
    return {}


def _sanitize_phone_number(value: str) -> str:
    raw = str(value).strip()
    if not raw:
        return ""
    plus = raw.startswith("+")
    digits = "".join(ch for ch in raw if ch.isdigit())
    if len(digits) < 10 or len(digits) > 15:
        return ""
    return f"+{digits}" if plus else digits


def build_candidates(
    db: KhataDB,
    min_days: int | None = None,
    min_amount: float | None = None,
) -> list[ReminderCandidate]:
    rows = db.get_pending_ledgers_with_age()
    effective_min_days = settings.reminder_min_days if min_days is None else int(min_days)
    effective_min_amount = settings.reminder_min_amount if min_amount is None else float(min_amount)
    out: list[ReminderCandidate] = []
    for row in rows:
        balance = float(row["balance"])
        days = int(row["pending_days"])
        if balance < effective_min_amount or days < effective_min_days:
            continue
        score = round(balance * 0.7 + days * 10, 2)
        out.append(
            ReminderCandidate(
                name=str(row["name"]),
                balance=balance,
                pending_days=days,
                score=score,
            )
        )
    out.sort(key=lambda x: x.score, reverse=True)
    return out


def send_owner_suggestion(owner_number: str, candidate: ReminderCandidate) -> None:
    message = (
        f"🚨 Boss, {candidate.name} ke ₹{int(candidate.balance)} pichle "
        f"{candidate.pending_days} din se pending hain.\n"
        f"Kya main polite reminder bhej dun? Reply: 'haan bhej de {candidate.name}'"
    )
    send_text_message(owner_number, message)


def _pick_customer_profile(db: KhataDB | None, customer_name: str) -> tuple[float | None, int | None]:
    if db is None:
        return None, None
    rows = db.get_pending_ledgers_with_age()
    target = customer_name.strip().title()
    for row in rows:
        if str(row.get("name", "")).strip().title() == target:
            return float(row.get("balance", 0)), int(row.get("pending_days", 0))
    return None, None


def _build_personalized_reminder(customer_name: str, balance: float | None, pending_days: int | None) -> str:
    name = customer_name.strip().title()
    if balance is None or pending_days is None:
        return (
            f"Namaste {name} ji, aapka KwikKhata balance pending hai. "
            "Jab convenient ho payment clear kar dein. Dhanyavaad."
        )

    if pending_days >= 45 or balance >= 5000:
        return (
            f"Namaste {name} ji, ₹{int(balance)} pichle {pending_days} din se pending hai. "
            "Request hai ki aaj hi partial ya full payment share kar dein. Dhanyavaad."
        )
    if pending_days >= 15 or balance >= 1500:
        return (
            f"Namaste {name} ji, aapka ₹{int(balance)} ka balance {pending_days} din se pending hai. "
            "Kripya is week payment clear kar dein."
        )
    return (
        f"Namaste {name} ji, friendly reminder: ₹{int(balance)} pending hai. "
        "Jab convenient ho payment bhej dein. Shukriya."
    )


def send_customer_reminder(customer_name: str, db: KhataDB | None = None) -> bool:
    phonebook = _load_phonebook()
    to = phonebook.get(customer_name.title())
    if not to:
        return False
    balance, pending_days = _pick_customer_profile(db, customer_name)
    body = _build_personalized_reminder(customer_name, balance=balance, pending_days=pending_days)
    result = send_text_message(to, body)
    return bool(result.get("ok"))


def run_daily_owner_summary(db: KhataDB) -> dict:
    owner = settings.owner_whatsapp_number
    if not owner:
        return {"ok": False, "reason": "OWNER_WHATSAPP_NUMBER missing"}

    candidates = build_candidates(db)
    if not candidates:
        send_text_message(owner, "✅ Aaj ke liye koi high-priority vasooli reminder nahi hai.")
        return {"ok": True, "count": 0}

    top = candidates[:5]
    lines = ["📌 Aaj ke top vasooli targets:"]
    for i, c in enumerate(top, start=1):
        lines.append(f"{i}. {c.name}: ₹{int(c.balance)} ({c.pending_days} din pending)")
    lines.append("Reply example: haan bhej de Raju")
    send_text_message(owner, "\n".join(lines))
    return {"ok": True, "count": len(top)}
