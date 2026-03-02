from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from time import monotonic


@dataclass
class RateLimitResult:
    allowed: bool
    remaining: int
    retry_after_seconds: int


class InMemorySlidingWindowRateLimiter:
    """Simple in-memory sliding-window limiter for webhook abuse protection."""

    def __init__(self, limit: int, window_seconds: int):
        self.limit = max(1, int(limit))
        self.window_seconds = max(1, int(window_seconds))
        self._events: dict[str, deque[float]] = {}

    def check(self, key: str) -> RateLimitResult:
        now = monotonic()
        bucket = self._events.setdefault(key, deque())
        cutoff = now - self.window_seconds
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()

        if len(bucket) >= self.limit:
            retry_after = max(1, int(self.window_seconds - (now - bucket[0])))
            return RateLimitResult(allowed=False, remaining=0, retry_after_seconds=retry_after)

        bucket.append(now)
        remaining = max(0, self.limit - len(bucket))
        return RateLimitResult(allowed=True, remaining=remaining, retry_after_seconds=0)
