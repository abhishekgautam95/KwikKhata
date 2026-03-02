from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from ai_parser import parse_shopkeeper_intent
from database import KhataDB
from services.reminder_engine import send_customer_reminder


def _fmt_money(value: float | int) -> str:
    value = float(value)
    if value.is_integer():
        return str(int(value))
    return f"{value:.2f}"


def _section(title: str, lines: list[str]) -> str:
    return "\n".join([f"✨ {title}", "─" * 48, *lines])


def _parse_manual_command(user_input: str) -> dict | None:
    text = user_input.strip()
    lower = text.lower()
    compact = re.sub(r"\s+", " ", lower).strip()

    if compact in {
        "ok",
        "okay",
        "ok good",
        "good",
        "great",
        "nice",
        "thik",
        "theek",
        "haan",
        "yes",
        "thanks",
        "thank you",
        "done",
    }:
        return {"customer_name": "", "action": "ack", "amount": 0}

    if (
        "kese ho" in compact
        or "kaise ho" in compact
        or "how are you" in compact
        or "kya kya" in compact
        or "kya kr sakte" in compact
        or "kya kar sakte" in compact
        or "what can you do" in compact
    ):
        return {"customer_name": "", "action": "smalltalk_help", "amount": 0}

    if text == "/remind-all":
        return {"customer_name": "", "action": "send_reminders", "amount": 0}
    if text == "/cleanup-names":
        return {"customer_name": "", "action": "cleanup_names", "amount": 0}
    merge_match = re.match(r"^/merge\s+(.+?)\s*->\s*(.+)$", text)
    if merge_match:
        source = merge_match.group(1).strip().title()
        target = merge_match.group(2).strip().title()
        return {"customer_name": "", "action": "merge_customer", "amount": 0, "source": source, "target": target}

    has_message_word = any(word in lower for word in {"message", "msg", "reminder", "bhej", "yaad"})
    has_group_word = any(
        phrase in lower
        for phrase in {"jis jis", "jinko", "jin ko", "jinpe", "jin pr", "jin par", "sabko", "sab ko", "all"}
    )
    has_due_word = any(
        phrase in lower
        for phrase in {"paisa", "paise", "udhaar", "udhar", "pending", "dene", "baki", "baaki", "de de", "vasooli"}
    )
    if has_message_word and has_group_word and has_due_word:
        return {"customer_name": "", "action": "send_reminders", "amount": 0}

    if text == "/all":
        return {"customer_name": "", "action": "get_all", "amount": 0}
    if text == "/undo":
        return {"customer_name": "", "action": "undo", "amount": 0}
    recent_match = re.match(r"^/recent(?:\s+(\d+))?$", text)
    if recent_match:
        limit = int(recent_match.group(1) or 10)
        return {"customer_name": "", "action": "recent", "amount": 0, "limit": max(1, limit)}
    if text.startswith("/bal "):
        name = text[5:].strip().title()
        return {"customer_name": name, "action": "get_balance", "amount": 0}
    history_match = re.match(r"^/history\s+(.+?)(?:\s+(\d+))?$", text)
    if history_match:
        name = history_match.group(1).strip().title()
        limit = int(history_match.group(2) or 10)
        return {"customer_name": name, "action": "history", "amount": 0, "limit": max(1, limit)}
    add_match = re.match(r"^/add\s+(.+?)\s+(-?\d+(?:\.\d+)?)$", text)
    if add_match:
        name = add_match.group(1).strip().title()
        amount = int(float(add_match.group(2)))
        return {"customer_name": name, "action": "add_transaction", "amount": abs(amount)}
    pay_match = re.match(r"^/pay\s+(.+?)\s+(-?\d+(?:\.\d+)?)$", text)
    if pay_match:
        name = pay_match.group(1).strip().title()
        amount = int(float(pay_match.group(2)))
        return {"customer_name": name, "action": "add_transaction", "amount": -abs(amount)}
    return None


def _tx_lines(rows: list[dict], title: str) -> str:
    if not rows:
        return f"📭 {title}: koi entries nahi mili."
    lines = []
    for row in rows:
        ts = row.get("timestamp") or "-"
        name = row.get("name") or "-"
        amount = float(row.get("amount") or 0)
        new_balance = float(row.get("new_balance") or 0)
        sign = "+" if amount >= 0 else "-"
        lines.append(f"• {ts} | {name} | {sign}₹{_fmt_money(abs(amount))} | bal ₹{_fmt_money(new_balance)}")
    return _section(title, lines)


def _execute_intent(db: KhataDB, data: dict) -> str:
    action = data.get("action")
    if action == "add_transaction":
        name = data.get("customer_name", "").strip()
        amount = float(data.get("amount", 0))
        if not name:
            return "❌ Customer ka naam missing hai."
        old_balance = db.get_balance(name) or 0
        new_balance = db.add_transaction(name, amount)
        if amount >= 0:
            return (
                f"✅ Done Boss! {name} ka ₹{_fmt_money(amount)} udhaar add kar diya.\n"
                f"Balance: ₹{_fmt_money(old_balance)} -> ₹{_fmt_money(new_balance)}"
            )
        return (
            f"✅ Done Boss! {name} se ₹{_fmt_money(abs(amount))} jama mark kar diya.\n"
            f"Balance: ₹{_fmt_money(old_balance)} -> ₹{_fmt_money(new_balance)}"
        )

    if action == "get_balance":
        name = data.get("customer_name", "").strip()
        if not name:
            return "❌ Kiska balance chahiye? Example: /bal Raju"
        bal = db.get_balance(name)
        if bal is None:
            return f"❌ '{name}' ka record nahi mila."
        return _section("Customer Balance", [f"👤 {name}", f"💰 Outstanding: ₹{_fmt_money(bal)}"])

    if action == "get_all":
        ledgers = db.get_all_ledgers()
        if not ledgers:
            return "📋 Kisi ka bhi udhaar pending nahi hai. Sab clear!"
        total = 0.0
        lines: list[str] = []
        for row in ledgers:
            total += float(row["balance"])
            lines.append(f"• {row['name']}: ₹{_fmt_money(row['balance'])}")
        lines.append("")
        lines.append(f"💼 Total Pending: ₹{_fmt_money(total)}")
        return _section("Pending Udhaar Leaderboard", lines)

    if action == "undo":
        undone = db.undo_last_transaction()
        if not undone:
            return "ℹ️ Undo ke liye koi recent transaction nahi mila."
        amount = float(undone["amount"])
        if amount >= 0:
            return (
                f"↩️ Undo done: {undone['customer_name']} ka ₹{_fmt_money(amount)} udhaar hata diya.\n"
                f"Updated balance: ₹{_fmt_money(undone['new_balance'])}"
            )
        return (
            f"↩️ Undo done: {undone['customer_name']} ki ₹{_fmt_money(abs(amount))} jama entry hata di.\n"
            f"Updated balance: ₹{_fmt_money(undone['new_balance'])}"
        )

    if action == "recent":
        limit = int(data.get("limit", 10))
        rows = db.get_recent_transactions(limit=limit)
        return _tx_lines(rows, f"Recent {limit} Transactions")

    if action == "history":
        name = str(data.get("customer_name", "")).strip()
        if not name:
            return "❌ Kiska history chahiye? Example: /history Raju 5"
        limit = int(data.get("limit", 10))
        rows = db.get_customer_transactions(name, limit=limit)
        return _tx_lines(rows, f"{name} ki last {limit} entries")

    if action == "send_reminders":
        ledgers = db.get_all_ledgers()
        if not ledgers:
            return "📋 Kisi ka bhi udhaar pending nahi hai, reminder bhejne ki zarurat nahi."
        sent_names: list[str] = []
        missing_names: list[str] = []
        for row in ledgers:
            name = str(row.get("name", "")).strip()
            if not name:
                continue
            if send_customer_reminder(name):
                sent_names.append(name)
            else:
                missing_names.append(name)
        if not sent_names:
            return "❌ Reminder nahi bhej paaya. CUSTOMER_PHONEBOOK me customer numbers set karein."
        response = [f"✅ {len(sent_names)} customer ko reminder bhej diya: {', '.join(sent_names)}"]
        if missing_names:
            response.append(f"⚠️ Number missing/failed: {', '.join(missing_names)}")
        return _section("Reminder Dispatch Report", response)

    if action == "cleanup_names":
        result = db.cleanup_noisy_customer_names()
        if not result.get("ok"):
            return "❌ Name cleanup failed."
        updated = int(result.get("updated", 0))
        if updated == 0:
            return "ℹ️ Koi noisy customer name cleanup ke liye nahi mila."
        lines = [f"✅ {updated} noisy customer names cleanup/merge kiye:"]
        for row in result.get("details", []):
            lines.append(f"• {row['source']} -> {row['target']} (bal: ₹{_fmt_money(row['new_balance'])})")
        return _section("Name Cleanup Summary", lines)

    if action == "merge_customer":
        source = str(data.get("source", "")).strip()
        target = str(data.get("target", "")).strip()
        if not source or not target:
            return "❌ Merge format: /merge Old Name -> New Name"
        result = db.merge_customers(source, target)
        if not result.get("ok"):
            return f"❌ Merge failed: {result.get('reason', 'unknown error')}"
        return _section(
            "Customer Merge Complete",
            [
                f"✅ {result['source']} -> {result['target']}",
                f"💰 Updated balance: ₹{_fmt_money(result['new_balance'])}",
            ],
        )

    if action == "ack":
        return "👍 Great. Agla command boliye: /all, /bal Raju, /add Raju 500"

    if action == "smalltalk_help":
        return _section(
            "Main Ye Kaam Kar Sakta Hoon",
            [
                "• /add Raju 500",
                "• /pay Raju 200",
                "• /bal Raju",
                "• /all, /recent, /history Raju",
                "• /remind-all, /cleanup-names, /merge Old -> New",
            ],
        )

    return "❌ Unknown action."


@dataclass
class AgentResponse:
    text: str
    needs_confirmation: bool = False


class PendingIntentStore:
    def __init__(self) -> None:
        self._store: dict[str, dict[str, Any]] = {}

    def get(self, user_id: str) -> dict[str, Any] | None:
        return self._store.get(user_id)

    def set(self, user_id: str, payload: dict[str, Any]) -> None:
        self._store[user_id] = payload

    def clear(self, user_id: str) -> None:
        self._store.pop(user_id, None)


def process_user_text(db: KhataDB, store: PendingIntentStore, user_id: str, text: str) -> AgentResponse:
    message = text.strip()
    if not message:
        return AgentResponse("⚠️ Kuch toh boliye.")

    pending = store.get(user_id)
    if pending:
        normalized = message.lower()
        if normalized in {"y", "yes", "haan", "ha", "ok"}:
            store.clear(user_id)
            return AgentResponse(_execute_intent(db, pending))
        if normalized in {"n", "no", "nahi", "cancel"}:
            store.clear(user_id)
            return AgentResponse("👍 Thik hai, cancel kar diya.")
        store.clear(user_id)

    data = _parse_manual_command(message)
    if data is None:
        data = parse_shopkeeper_intent(message)

    if data is None:
        return AgentResponse("❌ Samajh nahi aaya. Try: /add, /pay, /bal, /all")

    action = data.get("action")
    name = str(data.get("customer_name", "")).strip()
    amount = float(data.get("amount", 0))
    is_ambiguous_add = action == "add_transaction" and name and amount != 0 and " " in message and "/add" not in message
    if is_ambiguous_add and not any(k in message.lower() for k in {"udhaar", "udhar", "jama", "pay", "payment"}):
        store.set(user_id, data)
        sign_text = "udhaar" if amount >= 0 else "jama"
        return AgentResponse(
            f"❓ Confirm kar dein: {name} ke naam ₹{_fmt_money(abs(amount))} {sign_text} entry karun? (yes/no)",
            needs_confirmation=True,
        )

    return AgentResponse(_execute_intent(db, data))
