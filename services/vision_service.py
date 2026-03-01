from __future__ import annotations

import json
import os
from typing import Any


def parse_bill_image(image_bytes: bytes, mime_type: str = "image/jpeg") -> dict[str, Any] | None:
    """
    Parse bill image and return structured entries.
    Returns:
    {
      "entries": [{"customer_name": "...", "amount": 120}],
      "notes": "optional"
    }
    """
    if not image_bytes:
        return None

    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        return None

    try:
        import google.generativeai as genai
    except Exception:
        return None

    genai.configure(api_key=api_key)
    model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    model = genai.GenerativeModel(model_name=model_name)
    prompt = (
        "You are a strict invoice-to-ledger extractor. Read this shop bill image and return JSON only.\n"
        "Schema: {\"entries\":[{\"customer_name\":\"string\",\"amount\":number}],\"notes\":\"string\"}\n"
        "Rules: amount positive for udhaar given, negative for payment received if explicitly mentioned.\n"
        "If uncertain, keep entries empty and explain in notes."
    )

    try:
        response = model.generate_content(
            [
                {"mime_type": mime_type, "data": image_bytes},
                prompt,
            ]
        )
        text = (response.text or "").strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1]
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0].strip()
        payload = json.loads(text)
        if not isinstance(payload.get("entries"), list):
            return None
        return payload
    except Exception:  # pragma: no cover - network path
        return None
