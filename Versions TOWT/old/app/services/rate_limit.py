"""DB-backed rate limiting helpers.

Sprint 2 security hardening (A2.5). Used by:

- ``auth_router`` to throttle brute-force login attempts per IP.
- ``portal_security`` to throttle token guessing on public portals.

Two public helpers:

``is_rate_limited(db, scope, identifier, max_attempts, window_s)``
    Returns True when the caller must be rejected (recent attempts over
    the limit).

``record_attempt(db, scope, identifier)``
    Writes a new row. A lazy purge of rows older than
    ``PURGE_RETENTION_SECONDS`` runs opportunistically to keep the
    table bounded without needing a cron.

Both helpers take an ``AsyncSession`` so callers can reuse the existing
request-scoped session and get the transactional guarantees for free.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rate_limit import RateLimitAttempt


# Rows older than this are considered stale and eligible for opportunistic purge.
PURGE_RETENTION_SECONDS = 24 * 3600


async def is_rate_limited(
    db: AsyncSession,
    scope: str,
    identifier: str,
    max_attempts: int,
    window_seconds: int,
) -> bool:
    """Return True when ``identifier`` has exceeded ``max_attempts`` within the window."""
    since = datetime.now(timezone.utc) - timedelta(seconds=window_seconds)
    result = await db.execute(
        select(func.count(RateLimitAttempt.id))
        .where(
            RateLimitAttempt.scope == scope,
            RateLimitAttempt.identifier == identifier,
            RateLimitAttempt.attempted_at >= since,
        )
    )
    count = result.scalar_one()
    return count >= max_attempts


async def record_attempt(db: AsyncSession, scope: str, identifier: str) -> None:
    """Persist a failed attempt and opportunistically purge stale rows."""
    db.add(RateLimitAttempt(scope=scope, identifier=identifier))
    # Don't await flush here — callers manage the transaction. We still want
    # the purge to happen in the same transaction so we issue it immediately.
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=PURGE_RETENTION_SECONDS)
    await db.execute(
        delete(RateLimitAttempt).where(RateLimitAttempt.attempted_at < cutoff)
    )


async def clear_attempts(db: AsyncSession, scope: str, identifier: str) -> None:
    """Drop all recorded attempts for ``(scope, identifier)``.

    Useful to reset the counter after a successful login so legitimate
    users are not locked out indefinitely because of past typos.
    """
    await db.execute(
        delete(RateLimitAttempt).where(
            RateLimitAttempt.scope == scope,
            RateLimitAttempt.identifier == identifier,
        )
    )
