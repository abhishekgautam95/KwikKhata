"""
main.py — KwikKhata Main Controller
===================================
Terminal-first controller for Phase 1/2 backend.
"""

from __future__ import annotations

import logging
import os
import re
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
    print("  Commands: /help, /all, /bal <name>, /add <name> <amt>, /pay <name> <amt>")
    print("  Exit: exit / quit / bye / band karo\n")


def print_help() -> None:
    print("\nQuick Commands:")
    print("  /help                  -> Help dikhaye")
    print("  /all                   -> Sab pending ledgers")
    print("  /bal Raju              -> Raju ka balance")
    print("  /add Raju 500          -> Udhaar add (+500)")
    print("  /pay Raju 200          -> Jama entry (-200)")


def handle_add_transaction(db: KhataDB, data: dict) -> str:
    name = data["customer_name"]
    amount = data["amount"]

    try:
        new_balance = db.add_transaction(name, amount)
    except ValueError as exc:
        return f"❌ Entry error: {exc}"

    if amount >= 0:
        return (
            f"✅ Done! {name} ka ₹{_fmt_money(amount)} udhaar likh diya hai.\n"
            f"   Naya balance: ₹{_fmt_money(new_balance)}"
        )

    return (
        f"✅ Done! {name} se ₹{_fmt_money(abs(amount))} jama ho gaye.\n"
        f"   Naya balance: ₹{_fmt_money(new_balance)}"
    )


def handle_get_balance(db: KhataDB, data: dict) -> str:
    name = data["customer_name"]
    balance = db.get_balance(name)
    if balance is None:
        return f"❌ '{name}' ka koi record nahi mila."
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


def parse_manual_command(user_input: str) -> dict | None:
    text = user_input.strip()

    if text == "/all":
        return {"customer_name": "", "action": "get_all", "amount": 0}

    if text.startswith("/bal "):
        name = text[5:].strip().title()
        return {"customer_name": name, "action": "get_balance", "amount": 0}

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

        LOGGER.info("Input received: %s", user_input)
        data = parse_manual_command(user_input)
        if data is None:
            print("\n🤖 Samajh raha hoon...")
            data = parse_shopkeeper_intent(user_input)

        if data is None:
            LOGGER.warning("Intent parsing failed for input: %s", user_input)
            print("❌ Maaf kijiye, samajh nahi aaya. Thoda aur detail mein boliye.")
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
        else:
            response = "❌ Unknown action."
            LOGGER.warning("Unknown action payload: %s", data)

        print(f"\n{response}")


if __name__ == "__main__":
    main()
