"""
main.py — KwikKhata Main Controller
===================================
Terminal-first controller for Phase 1/2 backend.
"""

from __future__ import annotations

import logging
import os
import re
from itertools import cycle
from logging.handlers import RotatingFileHandler

from ai_parser import parse_shopkeeper_intent
from database import KhataDB


def _configure_logging() -> logging.Logger:
    os.makedirs("logs", exist_ok=True)
    logger = logging.getLogger("kwikkhata")
    logger.setLevel(logging.INFO)
    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        "%Y-%m-%d %H:%M:%S",
    )

    file_handler = RotatingFileHandler(
        "logs/kwikkhata.log",
        maxBytes=1_000_000,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger


LOGGER = _configure_logging()
_ADD_PREFIXES = cycle(["✅ Done!", "✅ Ho gaya!", "✅ Kar diya!"])
_PAY_PREFIXES = cycle(["✅ Done!", "✅ Entry ho gayi!", "✅ Jama note kar liya!"])


def _fmt_money(value: float | int) -> str:
    value = float(value)
    if value.is_integer():
        return str(int(value))
    return f"{value:.2f}"


def print_banner() -> None:
    print("\n" + "=" * 56)
    print("  KwikKhata - Aapka Digital Udhaar Khata")
    print("=" * 56)
    print("  Hinglish mein boliye, hum samajh jayenge!")
    print("  Commands: /help, /all, /bal <name>, /add <name> <amt>, /pay <name> <amt>, /undo, /recent, /history <name>")
    print("  Exit: exit / quit / bye / band karo\n")


def print_help() -> None:
    print("\nQuick Commands:")
    print("  /help                  -> Help dikhaye")
    print("  /all                   -> Sab pending ledgers")
    print("  /bal Raju              -> Raju ka balance")
    print("  /add Raju 500          -> Udhaar add (+500)")
    print("  /pay Raju 200          -> Jama entry (-200)")
    print("  /undo                  -> Last transaction undo")
    print("  /recent [n]            -> Latest n transactions (default 10)")
    print("  /history Raju [n]      -> Raju ki recent entries (default 10)")


def handle_add_transaction(db: KhataDB, data: dict) -> str:
    name = data["customer_name"]
    amount = data["amount"]

    try:
        old_balance = db.get_balance(name) or 0
        new_balance = db.add_transaction(name, amount)
    except ValueError as exc:
        return f"❌ Entry error: {exc}\nTry: /add <name> <amount> ya /pay <name> <amount>"

    if amount >= 0:
        return (
            f"{next(_ADD_PREFIXES)} {name} ka ₹{_fmt_money(amount)} udhaar likh diya.\n"
            f"   Balance: ₹{_fmt_money(old_balance)} -> ₹{_fmt_money(new_balance)}"
        )

    return (
        f"{next(_PAY_PREFIXES)} {name} se ₹{_fmt_money(abs(amount))} jama mark kar diya.\n"
        f"   Balance: ₹{_fmt_money(old_balance)} -> ₹{_fmt_money(new_balance)}"
    )


def handle_get_balance(db: KhataDB, data: dict) -> str:
    name = data["customer_name"]
    balance = db.get_balance(name)
    if balance is None:
        return f"❌ '{name}' ka record nahi mila. Try: /all ya /add {name} 100"
    return f"📊 {name} ka balance: ₹{_fmt_money(balance)}"


def handle_get_all(db: KhataDB) -> str:
    ledgers = db.get_all_ledgers()
    if not ledgers:
        return "📋 Kisi ka bhi udhaar pending nahi hai. Sab clear!"

    lines = ["📋 Pending Udhaar List:", "-" * 34]
    total = 0.0
    for entry in ledgers:
        lines.append(f"  - {entry['name']}: ₹{_fmt_money(entry['balance'])}")
        total += float(entry["balance"])
    lines.extend(["-" * 34, f"  Total Pending: ₹{_fmt_money(total)}"])
    return "\n".join(lines)


def handle_undo(db: KhataDB) -> str:
    undone = db.undo_last_transaction()
    if undone is None:
        return "ℹ️ Undo ke liye koi recent transaction nahi mila."

    name = undone["customer_name"]
    amount = float(undone["amount"])
    new_balance = float(undone["new_balance"])
    if amount >= 0:
        return (
            f"↩️ Last entry undo ho gayi: {name} ka ₹{_fmt_money(amount)} udhaar hata diya.\n"
            f"   Updated balance: ₹{_fmt_money(new_balance)}"
        )
    return (
        f"↩️ Last entry undo ho gayi: {name} ki ₹{_fmt_money(abs(amount))} jama entry hata di.\n"
        f"   Updated balance: ₹{_fmt_money(new_balance)}"
    )


def _format_tx_lines(tx_rows: list[dict], title: str) -> str:
    if not tx_rows:
        return f"📭 {title}: koi entries nahi mili."

    lines = [f"🧾 {title}", "-" * 46]
    for row in tx_rows:
        ts = row.get("timestamp") or "-"
        name = row.get("name") or "-"
        amount = float(row.get("amount") or 0)
        new_balance = float(row.get("new_balance") or 0)
        sign = "+" if amount >= 0 else "-"
        lines.append(
            f"  - {ts} | {name} | {sign}₹{_fmt_money(abs(amount))} | bal ₹{_fmt_money(new_balance)}"
        )
    return "\n".join(lines)


def handle_recent(db: KhataDB, limit: int) -> str:
    tx_rows = db.get_recent_transactions(limit=limit)
    return _format_tx_lines(tx_rows, f"Recent {limit} Transactions")


def handle_history(db: KhataDB, name: str, limit: int) -> str:
    tx_rows = db.get_customer_transactions(name, limit=limit)
    return _format_tx_lines(tx_rows, f"{name} ki last {limit} entries")


def _is_yes(text: str) -> bool:
    return text.strip().lower() in {"y", "yes", "haan", "ha", "ok", "theek", "thik"}


def _is_no(text: str) -> bool:
    return text.strip().lower() in {"n", "no", "nah", "nahi", "cancel"}


def _intent_summary(data: dict) -> str:
    action = data.get("action")
    if action == "get_all":
        return "sab pending ledgers dikhau"
    if action == "get_balance":
        return f"{data.get('customer_name', '').strip()} ka balance bataun"
    amount = data.get("amount", 0)
    name = data.get("customer_name", "").strip()
    if amount >= 0:
        return f"{name} ke naam ₹{_fmt_money(amount)} udhaar add karun"
    return f"{name} ke naam ₹{_fmt_money(abs(amount))} jama entry karun"


def _assess_intent_confidence(user_input: str, data: dict) -> tuple[str, str | None]:
    text = user_input.strip().lower()
    action = data.get("action")
    name = str(data.get("customer_name", "")).strip()
    amount = data.get("amount", 0)

    if action == "get_all":
        return "high", None

    if action == "get_balance":
        if name:
            return "high", None
        return "low", "Kiska balance chahiye? Example: 'Raju ka balance' ya '/bal Raju'"

    if action == "add_transaction":
        if not name:
            return "low", "Customer ka naam missing hai. Example: '/add Raju 500'"
        if amount == 0:
            return "low", "Amount missing lag raha hai. Example: '/add Raju 500' ya '/pay Raju 200'"

        has_money = bool(re.search(r"(?:₹\s*)?\d", text))
        has_txn_word = any(
            word in text
            for word in ("udhaar", "udhar", "jama", "pay", "payment", "likho", "/add", "/pay", "de diya")
        )
        noisy_name = len(name.split()) > 2
        if noisy_name or (has_money and not has_txn_word):
            return "medium", None
        return "high", None

    return "low", "Ye command clear nahi hai. Try: /help"


def parse_manual_command(user_input: str) -> dict | None:
    text = user_input.strip()

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


def main() -> None:
    print_banner()
    db = KhataDB()
    LOGGER.info("KwikKhata started")
    pending_intent: dict | None = None

    while True:
        try:
            user_input = input("\nKwikKhata: Boliye kya entry karni hai?\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            LOGGER.info("Session ended by interrupt")
            print("\n\n👋 KwikKhata band ho raha hai. Phir milenge!")
            break

        if user_input.lower() in {"exit", "quit", "bye", "band karo"}:
            LOGGER.info("Session closed by user command")
            print("\n👋 KwikKhata band ho raha hai. Phir milenge!")
            break

        if not user_input:
            print("⚠️  Kuch toh boliye!")
            continue

        if user_input == "/help":
            print_help()
            continue

        if pending_intent is not None:
            if _is_yes(user_input):
                data = pending_intent
                pending_intent = None
                print("👍 Confirmed. Execute kar raha hoon...")
            elif _is_no(user_input):
                pending_intent = None
                print("👍 Thik hai, cancel kar diya. Naya input boliye.")
                continue
            else:
                pending_intent = None
                print("ℹ️ Previous confirmation cancel. Is input ko fresh request maan rahe hain.")
                data = None
        else:
            data = None

        LOGGER.info("Input received: %s", user_input)
        if data is None:
            data = parse_manual_command(user_input)
        if data is None:
            print("\n🤖 Samajh raha hoon...")
            data = parse_shopkeeper_intent(user_input)
            if data is not None:
                confidence, reason = _assess_intent_confidence(user_input, data)
                if confidence == "low":
                    print(f"❓ {reason}")
                    continue
                if confidence == "medium":
                    pending_intent = data
                    print(f"❓ Confirm kar dein: {_intent_summary(data)}? (yes/no)")
                    continue

        if data is None:
            LOGGER.warning("Intent parsing failed for input: %s", user_input)
            print("❌ Samajh nahi aaya. Try: '/add Raju 200', '/pay Raju 100', '/bal Raju', '/all'")
            continue

        action = data.get("action")
        LOGGER.info("Resolved action: %s | payload=%s", action, data)

        if action == "add_transaction":
            if not data.get("customer_name"):
                print("❌ Customer ka naam missing hai.")
                continue
            response = handle_add_transaction(db, data)
        elif action == "get_balance":
            if not data.get("customer_name"):
                print("❌ Kiska balance chahiye? Naam boliye.")
                continue
            response = handle_get_balance(db, data)
        elif action == "get_all":
            response = handle_get_all(db)
        elif action == "undo":
            response = handle_undo(db)
        elif action == "recent":
            response = handle_recent(db, int(data.get("limit", 10)))
        elif action == "history":
            if not data.get("customer_name"):
                print("❌ Kiska history chahiye? Example: /history Raju")
                continue
            response = handle_history(db, str(data["customer_name"]), int(data.get("limit", 10)))
        else:
            response = "❌ Unknown action."
            LOGGER.warning("Unknown action payload: %s", data)

        print(f"\n{response}")


if __name__ == "__main__":
    main()
