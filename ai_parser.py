"""
ai_parser.py — KwikKhata AI Brain Module
========================================
Hybrid parser for Hinglish shopkeeper inputs.

Parsing strategy:
1. Fast local rule parser for common patterns (no API call).
2. LLM parser (Ollama/Gemini) for ambiguous messages.
3. Optional fallback provider chain.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

ALLOWED_ACTIONS = {"add_transaction", "get_balance", "get_all"}

# ---------------------------------------------------------------------------
# Rule-based parser
# ---------------------------------------------------------------------------
GET_ALL_KEYWORDS = {
    "sabka hisaab",
    "sab ka hisaab",
    "poora khata",
    "pura khata",
    "sab dikhao",
    "all customers",
    "sabka balance",
    "sab ka balance",
    "all pending",
    "sab ka udhaar",
}

BALANCE_KEYWORDS = {
    "balance",
    "kitna baki",
    "kitna baaki",
    "hisaab batao",
    "kitna udhaar",
    "kitna dena",
    "kitna lena",
    "baaki",
}

PAYMENT_KEYWORDS = {
    "jama",
    "vasool",
    "payment",
    "wapas",
    "paise diye",
    "de gaya",
    "de diye",
    "return",
}

CREDIT_KEYWORDS = {
    "udhaar",
    "udhar",
    "credit",
    "khata mein",
    "likho",
}

NAME_STOPWORDS = {
    "ka",
    "ki",
    "ko",
    "ne",
    "se",
    "mein",
    "me",
    "hai",
    "tha",
    "thi",
    "kar",
    "karo",
    "karlo",
    "karlo",
}


@dataclass
class ParseIntent:
    customer_name: str
    action: str
    amount: int

    def as_dict(self) -> dict:
        return {
            "customer_name": self.customer_name,
            "action": self.action,
            "amount": self.amount,
        }


def _normalize_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _extract_amount(text: str) -> int | None:
    # Supports inputs like: 500, ₹500, 1,500, 1500/-
    match = re.search(r"(?:₹\s*)?(-?\d[\d,]*)\s*(?:/-)?", text)
    if not match:
        return None
    number = match.group(1).replace(",", "")
    try:
        return int(number)
    except ValueError:
        return None


def _title_case_name(name: str) -> str:
    return _normalize_spaces(name).title()


def _extract_name(text: str) -> str:
    # Common patterns: "Raju ka ...", "Sharma ji ne ...", "Ravi ko ..."
    patterns = [
        r"^([a-zA-Z][a-zA-Z\s]{1,40}?)\s+(?:ka|ki|ko|ne|se)\b",
        r"^([a-zA-Z][a-zA-Z\s]{1,40}?)\s+(?:ka|ki|ko|ne|se)\b",
        r"^([a-zA-Z][a-zA-Z\s]{1,40})\b",
    ]

    cleaned = re.sub(r"[^a-zA-Z\s]", " ", text)
    cleaned = _normalize_spaces(cleaned.lower())

    for pattern in patterns:
        match = re.search(pattern, cleaned)
        if match:
            raw = _normalize_spaces(match.group(1))
            tokens = [t for t in raw.split() if t not in NAME_STOPWORDS]
            if tokens:
                return _title_case_name(" ".join(tokens))
    return ""


def _contains_any(text: str, keywords: set[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def _parse_intent_by_rules(user_text: str) -> ParseIntent | None:
    text = _normalize_spaces(user_text.lower())
    if not text:
        return None

    if _contains_any(text, GET_ALL_KEYWORDS):
        return ParseIntent(customer_name="", action="get_all", amount=0)

    name = _extract_name(text)

    # Balance check intent
    if _contains_any(text, BALANCE_KEYWORDS):
        if not name:
            return None
        return ParseIntent(customer_name=name, action="get_balance", amount=0)

    amount = _extract_amount(text)
    if amount is None:
        return None

    is_payment = _contains_any(text, PAYMENT_KEYWORDS)
    is_credit = _contains_any(text, CREDIT_KEYWORDS)

    # Heuristic: if only payment words => negative, else default positive
    if is_payment and not is_credit:
        amount = -abs(amount)
    elif is_credit and not is_payment:
        amount = abs(amount)
    else:
        # Ambiguous phrasing defaults to udhaar (positive) for safety in local parsing.
        amount = abs(amount)

    if not name:
        return None

    return ParseIntent(customer_name=name, action="add_transaction", amount=amount)


# ---------------------------------------------------------------------------
# Provider setup
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """
You are KwikKhata AI — a smart assistant for local shopkeepers in North India.
Your ONLY job is to understand a shopkeeper's Hinglish/Hindi message and extract
the intent as a strict JSON object. Do NOT include any extra text, markdown
formatting, or code fences — output ONLY the raw JSON.

Rules:
1) Udhaar / credit given => action=add_transaction, amount positive
2) Jama / payment received => action=add_transaction, amount negative
3) Check one customer balance => action=get_balance, amount 0
4) Show all pending => action=get_all, customer_name "", amount 0

Output schema:
{
  "customer_name": "String",
  "action": "add_transaction" | "get_balance" | "get_all",
  "amount": Integer
}
"""

GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
OLLAMA_MODEL_NAME = os.getenv("OLLAMA_MODEL", "llama3.2:latest")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434/api/generate")

AI_PROVIDER = os.getenv("AI_PROVIDER", "ollama").strip().lower()
FALLBACK_PROVIDER = os.getenv("FALLBACK_PROVIDER", "gemini").strip().lower()
ENABLE_FALLBACK = os.getenv("ENABLE_FALLBACK", "true").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
PARSER_MODE = os.getenv("PARSER_MODE", "hybrid").strip().lower()  # hybrid|llm


def _get_gemini_client():
    try:
        import google.generativeai as genai
    except ImportError as exc:
        raise RuntimeError(
            "google-generativeai package is not installed. Run: pip install -r requirements.txt"
        ) from exc

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is missing. Please set it in .env.")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        model_name=GEMINI_MODEL_NAME,
        system_instruction=SYSTEM_PROMPT,
    )
    return model, genai


def _validate_intent(result: dict) -> dict | None:
    required_keys = {"customer_name", "action", "amount"}
    if not required_keys.issubset(result.keys()):
        print("⚠️  AI response mein kuch fields missing hain.")
        return None

    if result["action"] not in ALLOWED_ACTIONS:
        print("⚠️  AI action invalid mila.")
        return None

    if not isinstance(result["customer_name"], str):
        print("⚠️  Customer name invalid format mein mila.")
        return None

    try:
        result["amount"] = int(result["amount"])
    except (TypeError, ValueError):
        print("⚠️  AI amount invalid mila.")
        return None

    if result["action"] != "add_transaction":
        result["amount"] = 0

    if result["action"] == "get_all":
        result["customer_name"] = ""
    else:
        result["customer_name"] = _title_case_name(result["customer_name"])

    return result


def _parse_with_gemini(user_text: str) -> dict | None:
    model, genai = _get_gemini_client()
    response = model.generate_content(
        user_text,
        generation_config=genai.types.GenerationConfig(
            temperature=0,
            response_mime_type="application/json",
        ),
    )
    raw_text = (response.text or "").strip()
    if not raw_text:
        print("⚠️  Gemini se empty response mila.")
        return None
    return _validate_intent(json.loads(raw_text))


def _parse_with_ollama(user_text: str) -> dict | None:
    payload = {
        "model": OLLAMA_MODEL_NAME,
        "prompt": f"{SYSTEM_PROMPT}\n\nInput: {user_text}\nOutput:",
        "format": "json",
        "stream": False,
        "options": {"temperature": 0},
    }

    req = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.URLError as exc:
        raise RuntimeError(
            "Ollama server unreachable. Ensure `ollama serve` is running on 127.0.0.1:11434."
        ) from exc

    envelope = json.loads(raw)
    raw_text = (envelope.get("response") or "").strip()
    if not raw_text:
        print("⚠️  Ollama se empty response mila.")
        return None

    if raw_text.startswith("```"):
        raw_text = raw_text.split("\n", 1)[1]
    if raw_text.endswith("```"):
        raw_text = raw_text.rsplit("```", 1)[0].strip()

    return _validate_intent(json.loads(raw_text))


def _parse_with_provider(provider: str, user_text: str) -> dict | None:
    if provider == "gemini":
        return _parse_with_gemini(user_text)
    if provider == "ollama":
        return _parse_with_ollama(user_text)
    raise RuntimeError("Unknown provider. Use 'ollama' or 'gemini'.")


def parse_shopkeeper_intent(user_text: str) -> dict | None:
    """Parse shopkeeper input into structured JSON-like dict."""
    try:
        if PARSER_MODE in {"hybrid", "rule", "rules"}:
            rule_result = _parse_intent_by_rules(user_text)
            if rule_result is not None:
                return rule_result.as_dict()

        # LLM parsing path for ambiguous messages.
        try:
            return _parse_with_provider(AI_PROVIDER, user_text)
        except Exception as primary_error:
            if not ENABLE_FALLBACK:
                raise primary_error

            if FALLBACK_PROVIDER == AI_PROVIDER:
                raise primary_error

            print(f"⚠️  {AI_PROVIDER.title()} unavailable. {FALLBACK_PROVIDER.title()} fallback try kar rahe hain...")
            return _parse_with_provider(FALLBACK_PROVIDER, user_text)

    except json.JSONDecodeError:
        print("⚠️  AI ka response samajh nahi aaya (invalid JSON).")
        return None
    except Exception as exc:
        print(f"⚠️  AI se baat karne mein dikkat aayi: {exc}")
        return None
