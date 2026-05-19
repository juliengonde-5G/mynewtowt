"""Security middlewares — force-change-password enforcement."""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import RedirectResponse, Response
from sqlalchemy import select

from app.auth import COOKIE_NAME, decode_session_token
from app.database import async_session
from app.models.user import User


# Paths that bypass force-change-password redirection.
# These cover: static assets, public portals, auth flow itself, and the
# change-password endpoint it would redirect to.
_EXEMPT_PREFIXES: tuple[str, ...] = (
    "/static/",
    "/.well-known/",
    "/login",
    "/logout",
    "/admin/my-account/change-password",
    "/admin/my-account/password",  # existing POST endpoint (already updates hash)
    # Public (token-based) portals and APIs — no session cookie in play
    "/p/",
    "/planning/share/",
    "/api/tracking/",
)

_CHANGE_PASSWORD_URL = "/admin/my-account/change-password"


class ForcePasswordChangeMiddleware(BaseHTTPMiddleware):
    """Redirect authenticated users with must_change_password=True to the
    change-password screen until they rotate their password.

    Kept as a dedicated middleware (vs. a dependency) to centralize the
    enforcement regardless of which route handles the current request.
    Reads the session cookie directly; on any failure mode falls through
    to the underlying handler so the existing auth flow stays authoritative.
    """

    async def dispatch(self, request, call_next):
        path = request.url.path
        if any(path.startswith(prefix) for prefix in _EXEMPT_PREFIXES):
            return await call_next(request)

        token = request.cookies.get(COOKIE_NAME)
        if not token:
            return await call_next(request)

        data = decode_session_token(token)
        if not data or "user_id" not in data:
            return await call_next(request)

        async with async_session() as db:
            result = await db.execute(
                select(User.must_change_password).where(
                    User.id == data["user_id"], User.is_active == True
                )
            )
            must_change = result.scalar_one_or_none()

        if not must_change:
            return await call_next(request)

        # HTMX clients need the redirect via response header, not 303
        if request.headers.get("HX-Request"):
            resp = Response(status_code=200)
            resp.headers["HX-Redirect"] = _CHANGE_PASSWORD_URL
            return resp
        return RedirectResponse(url=_CHANGE_PASSWORD_URL, status_code=303)
