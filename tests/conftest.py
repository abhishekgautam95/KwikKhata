"""
Common pytest fixtures for KwikKhata tests.
"""

from __future__ import annotations

import os
import tempfile

import pytest


@pytest.fixture()
def tmp_db_path(tmp_path):
    """Return a temporary file path suitable for a test database/Excel file."""
    return str(tmp_path / "test_kwikkhata.xlsx")


@pytest.fixture(autouse=False)
def mock_env(monkeypatch):
    """
    Patch common environment variables to safe test defaults.
    Usage: include ``mock_env`` as a parameter in any test that imports config.
    """
    env_overrides = {
        "APP_ENV": "test",
        "DATA_BACKEND": "excel",
        "PARSER_MODE": "hybrid",
        "AI_PROVIDER": "ollama",
        "ENABLE_FALLBACK": "false",
        "OLLAMA_URL": "http://127.0.0.1:19999/api/generate",
        "GEMINI_API_KEY": "",
        "WHATSAPP_VERIFY_TOKEN": "test-token",
        "WHATSAPP_ACCESS_TOKEN": "",
        "PII_HASH_SALT": "test-salt-for-pytest-only",
        "DASHBOARD_TOKEN": "test-dashboard",
        "PARTNER_API_KEYS": "test-key-1",
        "WEBHOOK_SIGNATURE_SECRET": "",
    }
    for key, value in env_overrides.items():
        monkeypatch.setenv(key, value)
    return env_overrides
