from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from database import create_db
from services.localization import format_currency

router = APIRouter(prefix="/api/v1", tags=["public-v1"])
db = create_db()


def _allowed_keys() -> set[str]:
    import os

    raw = os.getenv("PARTNER_API_KEYS", "").strip()
    return {v.strip() for v in raw.split(",") if v.strip()}


def _require_partner_key(key: str) -> None:
    allowed = _allowed_keys()
    if not allowed:
        raise HTTPException(status_code=503, detail="partner api keys not configured")
    if key.strip() not in allowed:
        raise HTTPException(status_code=403, detail="invalid api key")


def _safe_add_transaction(payload: dict[str, Any], idempotency_key: str | None = None) -> float:
    name = str(payload.get("customer_name", "")).strip()
    amount = float(payload.get("amount", 0))
    if hasattr(db, "add_transaction"):
        try:
            return float(db.add_transaction(name, amount, idempotency_key=idempotency_key, source="public_api"))
        except TypeError:
            return float(db.add_transaction(name, amount))
    raise RuntimeError("db backend missing add_transaction method")


class TransactionIn(BaseModel):
    customer_name: str = Field(min_length=1, max_length=120)
    amount: float


@router.get("/ledgers")
async def get_ledgers(x_api_key: str = Header(default="")):
    _require_partner_key(x_api_key)
    rows = db.get_all_ledgers()
    return {
        "ok": True,
        "count": len(rows),
        "items": [
            {
                "name": str(r["name"]),
                "balance": float(r["balance"]),
                "balance_display": format_currency(float(r["balance"])),
            }
            for r in rows
        ],
    }


@router.post("/transactions")
async def create_transaction(
    body: TransactionIn,
    x_api_key: str = Header(default=""),
    x_idempotency_key: str = Header(default=""),
):
    _require_partner_key(x_api_key)
    if body.amount == 0:
        raise HTTPException(status_code=422, detail="amount cannot be zero")
    new_balance = _safe_add_transaction(
        {"customer_name": body.customer_name, "amount": body.amount},
        idempotency_key=x_idempotency_key.strip() or None,
    )
    return {
        "ok": True,
        "customer_name": body.customer_name.strip().title(),
        "new_balance": round(float(new_balance), 2),
        "new_balance_display": format_currency(new_balance),
    }
