from __future__ import annotations

from datetime import datetime

from config import settings


def normalize_locale(locale: str | None) -> str:
    text = (locale or settings.default_locale).strip()
    if not text:
        return "en-IN"
    return text


def format_currency(amount: float | int, locale: str | None = None, currency: str | None = None) -> str:
    loc = normalize_locale(locale).lower()
    curr = (currency or settings.default_currency or "INR").upper()
    value = float(amount)
    if curr == "INR" or loc.endswith("-in"):
        return f"₹{int(value) if value.is_integer() else f'{value:.2f}'}"
    if curr == "USD" or loc.endswith("-us"):
        return f"${value:,.2f}"
    if curr == "EUR":
        return f"€{value:,.2f}"
    return f"{curr} {value:,.2f}"


def format_datetime(dt: datetime, locale: str | None = None) -> str:
    loc = normalize_locale(locale).lower()
    if loc.startswith("en-us"):
        return dt.strftime("%m/%d/%Y %I:%M %p")
    return dt.strftime("%d/%m/%Y %H:%M")


def localize_ack(locale: str | None = None) -> str:
    loc = normalize_locale(locale).lower()
    if loc.startswith("hi"):
        return "Thik hai, update ho gaya."
    return "Done, updated successfully."
