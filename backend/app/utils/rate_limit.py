"""Caps on how many photos get analysed, so a script can't run up the hosting bill.

Each photo costs a few seconds of CPU, so there are two limits:
- per visitor: a short burst and a daily total, keyed by IP address;
- for everyone together: a daily total, which holds even if someone spoofs their IP.

Counts live in memory. The server runs as a single instance, so that's enough, and a
restart resets them, which is fine for a cost guard.
"""

import os
import threading
import time
from collections import deque
from dataclasses import dataclass, field


def _env_int(name: str, default: int) -> int:
    try:
        return max(0, int(os.getenv(name, default)))
    except ValueError:
        return default


@dataclass
class Limits:
    per_minute: int = field(default_factory=lambda: _env_int("CIVICLENS_LIMIT_PER_MINUTE", 6))
    per_day: int = field(default_factory=lambda: _env_int("CIVICLENS_LIMIT_PER_DAY", 40))
    global_per_day: int = field(default_factory=lambda: _env_int("CIVICLENS_LIMIT_GLOBAL_PER_DAY", 400))


class RateLimiter:
    def __init__(self, limits: Limits | None = None, clock=time.monotonic) -> None:
        self.limits = limits or Limits()
        self.clock = clock
        self.lock = threading.Lock()
        self.visitors: dict[str, deque[float]] = {}
        self.everyone: deque[float] = deque()

    def check(self, visitor: str) -> int | None:
        """Count this request. Returns None if it may go ahead, otherwise seconds to wait."""
        now = self.clock()
        day_ago = now - 86_400
        with self.lock:
            while self.everyone and self.everyone[0] <= day_ago:
                self.everyone.popleft()
            times = self.visitors.setdefault(visitor, deque())
            while times and times[0] <= day_ago:
                times.popleft()
            # A limit of 0 switches analysis off; there's no oldest request to wait for then.
            if len(self.everyone) >= self.limits.global_per_day:
                return int(self.everyone[0] + 86_400 - now) + 1 if self.everyone else 86_400
            if len(times) >= self.limits.per_day:
                return int(times[0] + 86_400 - now) + 1 if times else 86_400
            recent = [t for t in times if t > now - 60]
            if len(recent) >= self.limits.per_minute:
                return int(recent[0] + 60 - now) + 1 if recent else 60
            times.append(now)
            self.everyone.append(now)
            # Forget visitors with nothing left in the window, so the map can't grow forever.
            if len(self.visitors) > 10_000:
                for key in [k for k, v in self.visitors.items() if not v]:
                    del self.visitors[key]
            return None


def visitor_of(forwarded_for: str | None, peer: str | None) -> str:
    """Cloud Run puts the caller's address in X-Forwarded-For. Its load balancer appends the
    real client address, so the last entry is the one a caller can't fake."""
    if forwarded_for:
        parts = [p.strip() for p in forwarded_for.split(",") if p.strip()]
        if parts:
            return parts[-1]
    return peer or "unknown"


limiter = RateLimiter()
