from __future__ import annotations

import json
import os
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
    if not raw:
        return {}
    try:
        payload = json.loads(raw)
        if isinstance(payload, dict):
            return {str(k).strip().title(): str(v).strip() for k, v in payload.items()}
    except Exception:
        return {}
    return {}


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


def send_customer_reminder(customer_name: str) -> bool:
    phonebook = _load_phonebook()
    to = phonebook.get(customer_name.title())
    if not to:
        return False
    body = (
        f"Namaste {customer_name} ji, aapka KwikKhata balance pending hai. "
        "Jab convenient ho payment clear kar dein. Dhanyavaad."
    )
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
