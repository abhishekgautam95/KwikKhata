"""
Centralized configuration for API and automation services.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, fields

from dotenv import load_dotenv

load_dotenv()

_VALID_BACKENDS = {"excel", "postgres"}
_SECRET_FIELD_KEYWORDS = {"key", "token", "secret", "password"}


def _mask_secret(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "***"
    return value[:4] + "***" + value[-2:]


@dataclass(frozen=True)
class Settings:
    app_env: str = os.getenv("APP_ENV", "dev")
    app_host: str = os.getenv("APP_HOST", "0.0.0.0")
    app_port: int = int(os.getenv("APP_PORT", "8000"))
    data_backend: str = os.getenv("DATA_BACKEND", "excel")
    database_url: str = os.getenv("KWIKKHATA_DATABASE_URL", os.getenv("DATABASE_URL", ""))
    webhook_rate_limit_per_minute: int = int(os.getenv("WEBHOOK_RATE_LIMIT_PER_MINUTE", "120"))
    webhook_rate_limit_window_seconds: int = int(os.getenv("WEBHOOK_RATE_LIMIT_WINDOW_SECONDS", "60"))
    webhook_max_payload_kb: int = int(os.getenv("WEBHOOK_MAX_PAYLOAD_KB", "256"))
    pii_hash_salt: str = os.getenv("PII_HASH_SALT", "")
    dashboard_token: str = os.getenv("DASHBOARD_TOKEN", "")
    default_response_mode: str = os.getenv("DEFAULT_RESPONSE_MODE", "rich")
    default_locale: str = os.getenv("DEFAULT_LOCALE", "en-IN")
    default_currency: str = os.getenv("DEFAULT_CURRENCY", "INR")
    compliance_store_file: str = os.getenv("COMPLIANCE_STORE_FILE", "logs/compliance_events.jsonl")
    compliance_retention_days: int = int(os.getenv("COMPLIANCE_RETENTION_DAYS", "365"))
    partner_api_keys: str = os.getenv("PARTNER_API_KEYS", "")
    webhook_signature_secret: str = os.getenv("WEBHOOK_SIGNATURE_SECRET", "")
    metrics_window_size: int = int(os.getenv("METRICS_WINDOW_SIZE", "2000"))

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

    def __repr__(self) -> str:
        parts = []
        for f in fields(self):
            value = getattr(self, f.name)
            if any(kw in f.name.lower() for kw in _SECRET_FIELD_KEYWORDS):
                value = _mask_secret(str(value))
            parts.append(f"{f.name}={value!r}")
        return f"Settings({', '.join(parts)})"

    def validate(self) -> list[str]:
        """Return a list of warning messages for misconfiguration."""
        warnings: list[str] = []
        if self.data_backend not in _VALID_BACKENDS:
            warnings.append(
                f"data_backend={self.data_backend!r} is invalid; choose from {sorted(_VALID_BACKENDS)}"
            )
        if self.data_backend == "postgres" and not self.database_url:
            warnings.append("data_backend is 'postgres' but KWIKKHATA_DATABASE_URL is not set")
        if not (1 <= self.app_port <= 65535):
            warnings.append(f"app_port={self.app_port} is outside valid range 1-65535")
        return warnings


settings = Settings()
