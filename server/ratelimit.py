"""Per-user rate limiting for the expensive LLM endpoints (start / stream / hint).

A token-bucket keyed by authenticated user id. State lives in this process, which
is fine for a single-instance deployment; if the API is scaled to multiple
machines, move the bucket store to a shared backend (e.g. Redis).
"""

import asyncio
import time
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, status

from deps import CurrentUser, get_current_user


@dataclass
class _Bucket:
    tokens: float
    updated: float


class RateLimiter:
    def __init__(self, rate: int, per_seconds: float) -> None:
        self.capacity = float(rate)
        self.refill = rate / per_seconds  # tokens per second
        self._buckets: dict[str, _Bucket] = {}
        self._lock = asyncio.Lock()

    async def check(self, key: str) -> None:
        async with self._lock:
            now = time.monotonic()
            bucket = self._buckets.get(key)
            if bucket is None:
                bucket = _Bucket(tokens=self.capacity, updated=now)
                self._buckets[key] = bucket
            bucket.tokens = min(
                self.capacity, bucket.tokens + (now - bucket.updated) * self.refill
            )
            bucket.updated = now
            if bucket.tokens < 1.0:
                retry_after = int((1.0 - bucket.tokens) / self.refill) + 1
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded. Please slow down.",
                    headers={"Retry-After": str(retry_after)},
                )
            bucket.tokens -= 1.0


# 20 lesson actions per minute per user, allowing short bursts up to the capacity.
_lesson_limiter = RateLimiter(rate=20, per_seconds=60.0)


async def lesson_rate_limit(
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> CurrentUser:
    await _lesson_limiter.check(user.user_id)
    return user


# Authenticates AND rate-limits; returns the current user like CurrentUserDep.
RateLimitedUserDep = Annotated[CurrentUser, Depends(lesson_rate_limit)]
