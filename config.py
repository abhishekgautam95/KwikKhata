"""
Centralized configuration for API and automation services.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    app_env: str = os.getenv("APP_ENV", "dev")
    app_host: str = os.getenv("APP_HOST", "0.0.0.0")
    app_port: int = int(os.getenv("APP_PORT", "8000"))

    whatsapp_verify_token: str = os.getenv("WHATSAPP_VERIFY_TOKEN", "")
    whatsapp_access_token: str = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
    whatsapp_phone_number_id: str = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
    whatsapp_business_account_id: str = os.getenv("WHATSAPP_BUSINESS_ACCOUNT_ID", "")
    whatsapp_graph_version: str = os.getenv("WHATSAPP_GRAPH_VERSION", "v21.0")
    whatsapp_api_base: str = os.getenv("WHATSAPP_API_BASE", "https://graph.facebook.com")

    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    whisper_model: str = os.getenv("WHISPER_MODEL", "gpt-4o-mini-transcribe")

    reminder_run_time: str = os.getenv("REMINDER_RUN_TIME", "10:00")
    reminder_min_days: int = int(os.getenv("REMINDER_MIN_DAYS", "15"))
    reminder_min_amount: float = float(os.getenv("REMINDER_MIN_AMOUNT", "500"))
    owner_whatsapp_number: str = os.getenv("OWNER_WHATSAPP_NUMBER", "")
    default_country_code: str = os.getenv("DEFAULT_COUNTRY_CODE", "+91")


settings = Settings()
