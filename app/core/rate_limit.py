from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Deque

from fastapi import HTTPException, status


@dataclass
class RateLimitDecision:
    allowed: bool
    remaining: int
    retry_after_seconds: int


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._events: dict[str, Deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str, *, limit: int, window_seconds: int) -> RateLimitDecision:
        now = time.time()
        cutoff = now - window_seconds
        with self._lock:
            events = self._events[key]
            while events and events[0] <= cutoff:
                events.popleft()

            if len(events) >= limit:
                retry_after = max(1, int(events[0] + window_seconds - now))
                return RateLimitDecision(False, 0, retry_after)

            events.append(now)
            remaining = max(0, limit - len(events))
            return RateLimitDecision(True, remaining, 0)


rate_limiter = InMemoryRateLimiter()


def enforce_rate_limit(key: str, *, limit: int, window_seconds: int, detail: str) -> None:
    decision = rate_limiter.check(key, limit=limit, window_seconds=window_seconds)
    if not decision.allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail,
            headers={'Retry-After': str(decision.retry_after_seconds)},
        )
