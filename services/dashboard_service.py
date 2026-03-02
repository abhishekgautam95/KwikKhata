from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta


def _risk_score(balance: float, pending_days: int) -> float:
    return round(balance * 0.6 + pending_days * 20, 2)


def _risk_label(score: float) -> str:
    if score >= 5000:
        return "high"
    if score >= 1500:
        return "medium"
    return "low"


def build_dashboard_summary(db, trend_days: int = 14) -> dict:
    rows = db.get_pending_ledgers_with_age()
    pending_total = round(sum(float(r["balance"]) for r in rows), 2)
    pending_count = len(rows)
    avg_pending_days = round(sum(int(r["pending_days"]) for r in rows) / pending_count, 2) if pending_count else 0.0

    customer_risk = []
    for row in rows:
        balance = float(row["balance"])
        days = int(row["pending_days"])
        score = _risk_score(balance, days)
        customer_risk.append(
            {
                "name": str(row["name"]),
                "balance": balance,
                "pending_days": days,
                "risk_score": score,
                "risk_label": _risk_label(score),
            }
        )
    customer_risk.sort(key=lambda x: x["risk_score"], reverse=True)
    top_risk = customer_risk[:5]

    # Collection trend: payments (negative amount) vs credit additions (positive amount)
    recent = db.get_recent_transactions(limit=1000)
    start = datetime.now() - timedelta(days=max(1, int(trend_days)))
    bucket: dict[str, dict[str, float]] = defaultdict(lambda: {"credited": 0.0, "collected": 0.0})
    for tx in recent:
        ts = str(tx.get("timestamp", ""))
        amount = float(tx.get("amount", 0))
        try:
            parsed = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
        except Exception:
            continue
        if parsed < start:
            continue
        key = parsed.strftime("%Y-%m-%d")
        if amount >= 0:
            bucket[key]["credited"] += amount
        else:
            bucket[key]["collected"] += abs(amount)

    trend = [
        {"date": day, "credited": round(v["credited"], 2), "collected": round(v["collected"], 2)}
        for day, v in sorted(bucket.items())
    ]

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "overview": {
            "pending_count": pending_count,
            "pending_total": pending_total,
            "avg_pending_days": avg_pending_days,
        },
        "top_risk_customers": top_risk,
        "collection_trend": trend,
    }
