import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status


class RateLimiter:
    """In-memory sliding-window limiter keyed by client IP (single process only)."""

    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def __call__(self, request: Request) -> None:
        key = request.client.host if request.client else "unknown"
        now = time.monotonic()
        hits = self._hits[key]
        while hits and now - hits[0] > self.window:
            hits.popleft()
        if len(hits) >= self.max_requests:
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS, "Too many requests, try later"
            )
        hits.append(now)

    def reset(self) -> None:
        self._hits.clear()


auth_rate_limiter = RateLimiter(max_requests=10, window_seconds=60)
