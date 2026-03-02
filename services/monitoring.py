from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime


@dataclass
class RequestSample:
    path: str
    method: str
    status_code: int
    latency_ms: float
    ts: str


class InMemoryMetrics:
    def __init__(self, window_size: int = 2000):
        self.window_size = max(100, int(window_size))
        self.samples: deque[RequestSample] = deque(maxlen=self.window_size)
        self.total_requests = 0
        self.total_errors = 0

    def record(self, path: str, method: str, status_code: int, latency_ms: float) -> None:
        self.total_requests += 1
        if int(status_code) >= 500:
            self.total_errors += 1
        self.samples.append(
            RequestSample(
                path=path,
                method=method,
                status_code=int(status_code),
                latency_ms=round(float(latency_ms), 2),
                ts=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            )
        )

    def snapshot(self) -> dict:
        recent = list(self.samples)
        count = len(recent)
        p95 = 0.0
        if count:
            sorted_lat = sorted(s.latency_ms for s in recent)
            idx = min(count - 1, int(count * 0.95))
            p95 = sorted_lat[idx]
        return {
            "total_requests": self.total_requests,
            "total_errors": self.total_errors,
            "window_count": count,
            "error_rate": round((self.total_errors / self.total_requests), 4) if self.total_requests else 0.0,
            "latency_p95_ms": round(p95, 2),
        }

    def slo(self, max_error_rate: float = 0.01, max_p95_ms: float = 800) -> dict:
        snap = self.snapshot()
        error_ok = snap["error_rate"] <= float(max_error_rate)
        latency_ok = snap["latency_p95_ms"] <= float(max_p95_ms) if snap["window_count"] else True
        return {
            "ok": bool(error_ok and latency_ok),
            "targets": {"max_error_rate": max_error_rate, "max_p95_ms": max_p95_ms},
            "current": snap,
            "status": {
                "error_budget_ok": error_ok,
                "latency_budget_ok": latency_ok,
            },
        }
