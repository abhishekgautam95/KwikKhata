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
from typing import Any

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
    "show me all",
    "sab show",
    "sab dikha",
    "sab dikhao",
    "kis kis",
    "kin kin",
    "all data",
    "sab data",
    "all records",
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

NAME_NOISE_WORDS = {
    "rupees",
    "rupaye",
    "rupay",
    "rs",
    "inr",
    "data",
    "record",
    "records",
    "entry",
    "entries",
    "pending",
    "show",
    "dikha",
    "dikhao",
    "check",
    "please",
    "pls",
    "chini",
    "cheeni",
    "daal",
    "dal",
    "namkeen",
    "biscuit",
    "biskut",
    "sabun",
    "soap",
    "tel",
    "oil",
    "atta",
    "chawal",
    "rice",
    "salt",
    "namak",
    "masala",
}

NAME_TITLE_SUFFIX = {"ji", "bhai", "bhaiya", "sir", "madam", "uncle", "aunty"}


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


def _clean_name_tokens(tokens: list[str]) -> list[str]:
    return [
        token
        for token in tokens
        if token and token not in NAME_STOPWORDS and token not in NAME_NOISE_WORDS
    ]


def _extract_name(text: str) -> str:
    # Prefer tokens before the first amount: "Aditya 30 rupees namkeen" -> "Aditya"
    amount_match = re.search(r"(?:₹\s*)?-?\d[\d,]*\s*(?:/-)?", text)
    if amount_match:
        before_amount = _normalize_spaces(text[: amount_match.start()].lower())
        before_amount = re.sub(r"[^a-z\s]", " ", before_amount)
        tokens = _clean_name_tokens(_normalize_spaces(before_amount).split())
        if tokens:
            return _title_case_name(" ".join(tokens[:3]))

        # Amount-first phrases like "30 rupees chini aditya" -> "Aditya"
        after_amount = _normalize_spaces(text[amount_match.end() :].lower())
        after_amount = re.sub(r"[^a-z\s]", " ", after_amount)
        after_tokens = _clean_name_tokens(_normalize_spaces(after_amount).split())
        if after_tokens:
            if len(after_tokens) >= 2 and after_tokens[-1] in NAME_TITLE_SUFFIX:
                return _title_case_name(" ".join(after_tokens[-2:]))
            return _title_case_name(after_tokens[-1])

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
            tokens = _clean_name_tokens(raw.split())
            if tokens:
                return _title_case_name(" ".join(tokens[:3]))
    return ""


def _contains_any(text: str, keywords: set[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def _looks_like_get_all_query(text: str) -> bool:
    if _contains_any(text, GET_ALL_KEYWORDS):
        return True

    # Queries like: "kis kis pe kitna baki hai", "kin kin ka hisaab show me"
    has_group_prompt = any(token in text for token in {"kis kis", "kin kin", "kiske", "kis pe", "kis par"})
    has_amount_context = any(token in text for token in {"kitna", "kitne", "baki", "baaki", "udhaar", "hisaab"})
    has_show_prompt = any(token in text for token in {"show", "dikha", "dikhao"})

    return has_group_prompt and (has_amount_context or has_show_prompt)


def _parse_intent_by_rules(user_text: str) -> ParseIntent | None:
    text = _normalize_spaces(user_text.lower())
    if not text:
        return None

    if _looks_like_get_all_query(text):
        return ParseIntent(customer_name="", action="get_all", amount=0)

    name = _extract_name(text)

    # Balance check intent
    if _contains_any(text, BALANCE_KEYWORDS):
        if not name:
            return None
        return ParseIntent(customer_name=name, action="get_balance", amount=0)

    # Short follow-up like: "sbi ka", "raju ki", "mohan ko"
    if name and re.match(r"^[a-z\s]+\s+(?:ka|ki|ko|se)\s*$", text):
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
MAX_ALLOWED_AMOUNT = int(os.getenv("KWIKKHATA_MAX_ALLOWED_AMOUNT", "10000000"))


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


def _deterministic_amount_direction(text: str, amount: int) -> tuple[int, str]:
    is_payment = _contains_any(text, PAYMENT_KEYWORDS)
    is_credit = _contains_any(text, CREDIT_KEYWORDS)
    if is_payment and not is_credit:
        return -abs(amount), "payment keyword detected"
    if is_credit and not is_payment:
        return abs(amount), "credit keyword detected"
    return amount, "direction unchanged"


def _deterministic_guardrails(user_text: str, parsed: dict | None) -> tuple[dict | None, dict[str, Any]]:
    if parsed is None:
        return None, {"confidence": "low", "risk": "high", "reason": "parser returned empty intent"}

    out = dict(parsed)
    text = _normalize_spaces(user_text.lower())
    action = str(out.get("action", "")).strip()
    name = _title_case_name(str(out.get("customer_name", "")).strip())
    amount = int(out.get("amount", 0) or 0)

    if action == "add_transaction":
        if not name:
            return None, {"confidence": "low", "risk": "high", "reason": "missing customer name"}
        if amount == 0:
            return None, {"confidence": "low", "risk": "high", "reason": "amount missing"}
        if abs(amount) > MAX_ALLOWED_AMOUNT:
            return None, {"confidence": "low", "risk": "high", "reason": "amount above allowed safety limit"}
        corrected_amount, direction_reason = _deterministic_amount_direction(text, amount)
        out["amount"] = corrected_amount
        has_txn_word = any(
            word in text for word in {"udhaar", "udhar", "jama", "pay", "payment", "credit", "de diya", "de diye"}
        )
        if not has_txn_word:
            return out, {
                "confidence": "medium",
                "risk": "high",
                "reason": f"amount parsed but transaction intent words are weak; {direction_reason}",
            }
        return out, {"confidence": "high", "risk": "medium", "reason": direction_reason}

    if action == "get_balance":
        if not name:
            return None, {"confidence": "low", "risk": "high", "reason": "missing customer name for balance lookup"}
        out["customer_name"] = name
        out["amount"] = 0
        return out, {"confidence": "high", "risk": "low", "reason": "single customer balance intent"}

    if action == "get_all":
        out["customer_name"] = ""
        out["amount"] = 0
        return out, {"confidence": "high", "risk": "low", "reason": "group ledger query intent"}

    return None, {"confidence": "low", "risk": "high", "reason": "unsupported action"}


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


def _repair_llm_intent(user_text: str, result: dict | None) -> dict | None:
    if result is None:
        return None

    text = _normalize_spaces(user_text.lower())
    action = result.get("action")
    customer_name = _title_case_name(result.get("customer_name", ""))

    # LLM sometimes returns get_balance without name for "all data" style queries.
    if action == "get_balance" and not customer_name:
        if _looks_like_get_all_query(text):
            return {"customer_name": "", "action": "get_all", "amount": 0}
        return None

    # Keep name tidy even when LLM returns noisy strings.
    if action in {"add_transaction", "get_balance"}:
        extracted_name = _extract_name(user_text)
        if extracted_name:
            result["customer_name"] = extracted_name
        else:
            result["customer_name"] = customer_name

    return result


def parse_shopkeeper_intent(user_text: str, include_meta: bool = False) -> dict | None:
    """Parse shopkeeper input into structured JSON-like dict."""
    try:
        parser_source = "llm"
        if PARSER_MODE in {"hybrid", "rule", "rules"}:
            rule_result = _parse_intent_by_rules(user_text)
            if rule_result is not None:
                parser_source = "rules"
                guarded, meta = _deterministic_guardrails(user_text, rule_result.as_dict())
                if guarded is None:
                    return None
                if include_meta:
                    guarded["_explain"] = {
                        "parser_source": parser_source,
                        "confidence": meta["confidence"],
                        "risk": meta["risk"],
                        "reason": meta["reason"],
                    }
                return guarded

        # LLM parsing path for ambiguous messages.
        try:
            llm_result = _parse_with_provider(AI_PROVIDER, user_text)
            parser_source = AI_PROVIDER
            repaired = _repair_llm_intent(user_text, llm_result)
            guarded, meta = _deterministic_guardrails(user_text, repaired)
            if guarded is None:
                return None
            if include_meta:
                guarded["_explain"] = {
                    "parser_source": parser_source,
                    "confidence": meta["confidence"],
                    "risk": meta["risk"],
                    "reason": meta["reason"],
                }
            return guarded
        except Exception as primary_error:
            if not ENABLE_FALLBACK:
                raise primary_error

            if FALLBACK_PROVIDER == AI_PROVIDER:
                raise primary_error

            print(f"⚠️  {AI_PROVIDER.title()} unavailable. {FALLBACK_PROVIDER.title()} fallback try kar rahe hain...")
            llm_result = _parse_with_provider(FALLBACK_PROVIDER, user_text)
            parser_source = FALLBACK_PROVIDER
            repaired = _repair_llm_intent(user_text, llm_result)
            guarded, meta = _deterministic_guardrails(user_text, repaired)
            if guarded is None:
                return None
            if include_meta:
                guarded["_explain"] = {
                    "parser_source": parser_source,
                    "confidence": meta["confidence"],
                    "risk": meta["risk"],
                    "reason": meta["reason"],
                }
            return guarded

    except json.JSONDecodeError:
        print("⚠️  AI ka response samajh nahi aaya (invalid JSON).")
        return None
    except Exception as exc:
        print(f"⚠️  AI se baat karne mein dikkat aayi: {exc}")
        return None
