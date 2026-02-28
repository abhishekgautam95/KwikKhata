"""
ai_parser.py — KwikKhata AI Brain Module
==========================================
Uses Google Gemini (via google-genai SDK) to parse Hinglish shopkeeper
messages into structured JSON intents (customer_name, action, amount).
"""

import json
import os

from google import genai
from dotenv import load_dotenv

# Load API key from .env
load_dotenv()

# Initialize the Gemini client
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# ---------------------------------------------------------------------------
# System prompt — teaches the LLM the shopkeeper's vocabulary
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """
You are KwikKhata AI — a smart assistant for local shopkeepers in North India.
Your ONLY job is to understand a shopkeeper's Hinglish/Hindi message and extract
the intent as a strict JSON object. Do NOT include any extra text, markdown
formatting, or code fences — output ONLY the raw JSON.

### Rules for understanding shopkeeper language:

1. **Udhaar / Credit given** (shopkeeper gave goods on credit):
   Keywords: "udhaar", "udhaar diya", "udhaar likho", "credit", "khata mein likho", "de diya"
   → action = "add_transaction", amount = POSITIVE (e.g., +500)

2. **Jama / Payment received** (customer paid money back):
   Keywords: "jama", "jama kar lo", "vasool", "wapas diya", "payment aaya",
              "de diya" (when context is about returning money), "paise diye"
   → action = "add_transaction", amount = NEGATIVE (e.g., -200)

3. **Check balance of one customer**:
   Keywords: "balance", "kitna baki hai", "hisaab batao", "kitna udhaar hai"
   → action = "get_balance", amount = 0

4. **Show all pending ledgers**:
   Keywords: "sabka hisaab", "poora khata", "sab dikhao", "all customers",
              "sabka balance"
   → action = "get_all", customer_name = "", amount = 0

### Output JSON schema (return ONLY this, nothing else):

{
  "customer_name": "<string — customer's name in Title Case>",
  "action": "add_transaction" | "get_balance" | "get_all",
  "amount": <integer — positive for udhaar, negative for jama, 0 otherwise>
}

### Examples:

Input: "Raju ka 500 udhaar likho"
Output: {"customer_name": "Raju", "action": "add_transaction", "amount": 500}

Input: "Sharma ji ne 200 jama kiya"
Output: {"customer_name": "Sharma Ji", "action": "add_transaction", "amount": -200}

Input: "Raju ka balance batao"
Output: {"customer_name": "Raju", "action": "get_balance", "amount": 0}

Input: "Sabka hisaab dikhao"
Output: {"customer_name": "", "action": "get_all", "amount": 0}

Input: "Raju ka 500 jama kar lo"
Output: {"customer_name": "Raju", "action": "add_transaction", "amount": -500}

Input: "Sharma ji ko 200 udhaar diya"
Output: {"customer_name": "Sharma Ji", "action": "add_transaction", "amount": 200}
"""

# ---------------------------------------------------------------------------
# Gemini model setup
# ---------------------------------------------------------------------------
MODEL_NAME = "gemini-2.0-flash"


def parse_shopkeeper_intent(user_text: str) -> dict | None:
    """
    Send the shopkeeper's Hinglish message to Gemini and extract a
    structured intent dict.

    Args:
        user_text: Raw message from the shopkeeper.

    Returns:
        A dict with keys: customer_name, action, amount.
        Returns None if parsing fails.
    """
    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=user_text,
            config={
                "system_instruction": SYSTEM_PROMPT,
            },
        )

        # Extract the text and parse JSON
        raw_text = response.text.strip()

        # Strip markdown code fences if the model wraps them anyway
        if raw_text.startswith("```"):
            raw_text = raw_text.split("\n", 1)[1]  # remove opening fence line
        if raw_text.endswith("```"):
            raw_text = raw_text.rsplit("```", 1)[0].strip()

        result = json.loads(raw_text)

        # Basic validation — ensure required keys exist
        required_keys = {"customer_name", "action", "amount"}
        if not required_keys.issubset(result.keys()):
            print("⚠️  AI response mein kuch fields missing hain.")
            return None

        # Ensure amount is an integer
        result["amount"] = int(result["amount"])

        return result

    except json.JSONDecodeError:
        print("⚠️  AI ka response samajh nahi aaya (invalid JSON).")
        return None
    except Exception as e:
        print(f"⚠️  AI se baat karne mein dikkat aayi: {e}")
        return None
