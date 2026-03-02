"""
Validate environment security posture for production deployments.
"""

from __future__ import annotations

import os


def _is_missing(name: str) -> bool:
    return not os.getenv(name, "").strip()


def _is_weak(value: str, min_len: int = 24) -> bool:
    return len(value.strip()) < min_len


def main() -> None:
    app_env = os.getenv("APP_ENV", "dev").strip().lower()
    issues: list[str] = []
    warnings: list[str] = []

    required_if_prod = [
        "WHATSAPP_VERIFY_TOKEN",
        "WHATSAPP_ACCESS_TOKEN",
        "PII_HASH_SALT",
    ]
    if app_env == "prod":
        for name in required_if_prod:
            if _is_missing(name):
                issues.append(f"missing required env: {name}")

    pii_salt = os.getenv("PII_HASH_SALT", "")
    if pii_salt and _is_weak(pii_salt):
        warnings.append("PII_HASH_SALT is short; use at least 24 chars.")

    access_token = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
    if access_token and _is_weak(access_token, min_len=32):
        warnings.append("WHATSAPP_ACCESS_TOKEN looks short.")

    backend = os.getenv("DATA_BACKEND", "excel").strip().lower()
    if backend == "postgres":
        if _is_missing("KWIKKHATA_DATABASE_URL") and _is_missing("DATABASE_URL"):
            issues.append("DATA_BACKEND=postgres but no database URL is set.")

    if warnings:
        print("WARNINGS:")
        for w in warnings:
            print(f"- {w}")
    if issues:
        print("ERRORS:")
        for i in issues:
            print(f"- {i}")
        raise SystemExit(1)

    print("Environment validation passed.")


if __name__ == "__main__":
    main()
