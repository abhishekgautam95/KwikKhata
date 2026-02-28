"""
main.py — KwikKhata Main Controller
=====================================
Interactive terminal loop that connects the AI parser with the
Excel-based ledger database. Speaks Hinglish with the shopkeeper.
"""

from database import KhataDB
from ai_parser import parse_shopkeeper_intent


def print_banner():
    """Print a friendly welcome banner."""
    print("\n" + "=" * 50)
    print("  📒  KwikKhata — Aapka Digital Udhaar Khata  📒")
    print("=" * 50)
    print("  Hinglish mein boliye, hum samajh jayenge!")
    print("  (Type 'exit' ya 'quit' to close)\n")


def handle_add_transaction(db: KhataDB, data: dict) -> str:
    """Handle an add_transaction intent and return a confirmation message."""
    name = data["customer_name"]
    amount = data["amount"]

    new_balance = db.add_transaction(name, amount)

    if amount >= 0:
        return (
            f"✅ Done! {name} ka ₹{amount} udhaar likh diya hai.\n"
            f"   Naya balance: ₹{new_balance}"
        )
    else:
        return (
            f"✅ Done! {name} se ₹{abs(amount)} jama ho gaye.\n"
            f"   Naya balance: ₹{new_balance}"
        )


def handle_get_balance(db: KhataDB, data: dict) -> str:
    """Handle a get_balance intent and return the result message."""
    name = data["customer_name"]
    balance = db.get_balance(name)

    if balance is not None:
        return f"📊 {name} ka balance: ₹{balance}"
    else:
        return f"❌ '{name}' ka koi record nahi mila. Pehle koi entry karein."


def handle_get_all(db: KhataDB) -> str:
    """Handle a get_all intent and return a summary of all ledgers."""
    ledgers = db.get_all_ledgers()

    if not ledgers:
        return "📋 Kisi ka bhi udhaar pending nahi hai. Sab clear! 🎉"

    lines = ["📋 Pending Udhaar List:"]
    lines.append("-" * 30)
    total = 0
    for entry in ledgers:
        lines.append(f"  • {entry['name']}: ₹{entry['balance']}")
        total += entry["balance"]
    lines.append("-" * 30)
    lines.append(f"  Total Pending: ₹{total}")

    return "\n".join(lines)


def main():
    """Main interactive loop."""
    print_banner()

    # Initialize the database
    db = KhataDB()

    while True:
        try:
            user_input = input("\n🗣️  KwikKhata: Boliye kya entry karni hai?\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\n👋 KwikKhata band ho raha hai. Phir milenge!")
            break

        # Exit commands
        if user_input.lower() in ("exit", "quit", "bye", "band karo"):
            print("\n👋 KwikKhata band ho raha hai. Phir milenge!")
            break

        if not user_input:
            print("⚠️  Kuch toh boliye! 😅")
            continue

        # Parse intent using AI
        print("\n🤖 Samajh raha hoon...")
        data = parse_shopkeeper_intent(user_input)

        if data is None:
            print("❌ Maaf kijiye, samajh nahi aaya. Thoda aur detail mein boliye.")
            continue

        # Route to the correct handler
        action = data.get("action")

        if action == "add_transaction":
            if not data.get("customer_name"):
                print("❌ Customer ka naam nahi mila. Please naam ke saath boliye.")
                continue
            response = handle_add_transaction(db, data)

        elif action == "get_balance":
            if not data.get("customer_name"):
                print("❌ Kiska balance chahiye? Customer ka naam boliye.")
                continue
            response = handle_get_balance(db, data)

        elif action == "get_all":
            response = handle_get_all(db)

        else:
            response = "❌ Yeh action samajh nahi aaya. Please dubara try karein."

        print(f"\n{response}")


if __name__ == "__main__":
    main()
