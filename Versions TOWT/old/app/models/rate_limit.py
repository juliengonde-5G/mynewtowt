"""Persistent rate limiting store.

Sprint 2 security hardening (A2.5): the in-memory dicts used by
``auth_router._login_attempts`` and ``portal_security._token_attempts``
were reset on every container restart and did not survive multi-instance
scale-out. This table persists the attempts instead.

Rows are written on every failed attempt. A periodic clean-up is handled
by ``purge_expired`` (called lazily when checking limits) — we do not
need a separate cron since the query filters on ``attempted_at`` anyway.
"""
from sqlalchemy import Column, Integer, String, DateTime, Index, func
from app.database import Base


class RateLimitAttempt(Base):
    __tablename__ = "rate_limit_attempts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # Scope discriminates between usages (e.g. "login", "portal_token").
    scope = Column(String(40), nullable=False, index=True)
    # Identifier is typically the source IP but could be a user id etc.
    identifier = Column(String(100), nullable=False, index=True)
    attempted_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        Index("ix_rate_limit_scope_id_time", "scope", "identifier", "attempted_at"),
    )
