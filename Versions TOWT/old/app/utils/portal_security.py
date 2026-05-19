"""
Portal security utilities: rate limiting on token lookups and access logging.
"""
import hashlib
import logging
from fastapi import HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.services import rate_limit as rl


def hash_portal_token(token: str) -> str:
    """Return the sha256 hex digest of a portal token.

    Used so portal_access_logs.token_hash never exposes the raw token.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


logger = logging.getLogger(__name__)

# ── Rate limiting for token-based portal access (DB-backed — A2.5) ──
_RL_SCOPE = "portal_token"
TOKEN_RATE_LIMIT = 10    # max failed attempts
TOKEN_RATE_WINDOW = 300  # per 5 minutes


async def check_token_rate_limit(request: Request, db: AsyncSession):
    """Rate-limit token validation attempts per IP. Call before token lookup."""
    ip = request.client.host if request.client else "unknown"
    if await rl.is_rate_limited(db, _RL_SCOPE, ip, TOKEN_RATE_LIMIT, TOKEN_RATE_WINDOW):
        logger.warning(f"Portal rate limit exceeded for IP {ip}")
        raise HTTPException(429, detail="Trop de tentatives. Réessayez dans quelques minutes.")


async def record_token_attempt(request: Request, db: AsyncSession):
    """Record a token lookup attempt (call on 404/invalid token)."""
    ip = request.client.host if request.client else "unknown"
    await rl.record_attempt(db, _RL_SCOPE, ip)


async def log_portal_access(db, request: Request, portal_type: str, token: str,
                            packing_list_id: int = None):
    """Log an access to an external portal for RGPD audit trail.

    Only the sha256 of the token is persisted (A2.3 hardening).
    """
    from app.models.portal_access_log import PortalAccessLog
    log_entry = PortalAccessLog(
        portal_type=portal_type,
        token_hash=hash_portal_token(token),
        ip_address=request.client.host if request.client else None,
        user_agent=(request.headers.get("user-agent", ""))[:500],
        path=str(request.url.path),
        packing_list_id=packing_list_id,
    )
    db.add(log_entry)
