"""Double-submit cookie CSRF protection.

Pose `towt_csrf` cookie sur toute réponse, exige un header `x-csrf-token`
ou un champ `_csrf` sur toute requête mutante (POST/PUT/PATCH/DELETE).

HTMX peut être configuré pour injecter le header automatiquement
(cf. `templates/base.html`).
"""
from __future__ import annotations

import secrets

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

CSRF_COOKIE = "towt_csrf"
CSRF_HEADER = "x-csrf-token"
CSRF_FORM_FIELD = "_csrf"
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
EXEMPT_PATHS_PREFIXES = (
    "/api/v1/",        # API expects its own auth (API key / bearer)
    "/webhooks/",      # external webhook integrations sign their payloads
    "/health",
    "/metrics",
)


class CSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Ensure cookie present
        cookie_value = request.cookies.get(CSRF_COOKIE) or secrets.token_urlsafe(32)
        set_cookie = CSRF_COOKIE not in request.cookies

        # Validate on mutating requests
        if (
            request.method not in SAFE_METHODS
            and not any(request.url.path.startswith(p) for p in EXEMPT_PATHS_PREFIXES)
        ):
            header_token = request.headers.get(CSRF_HEADER)
            form_token: str | None = None
            if not header_token and request.headers.get("content-type", "").startswith(
                "application/x-www-form-urlencoded"
            ):
                # Read the form once; cache in scope for downstream
                form = await request.form()
                form_token = form.get(CSRF_FORM_FIELD)
                request._form = form  # type: ignore[attr-defined]

            submitted = header_token or form_token
            if not submitted or submitted != cookie_value:
                return Response(
                    "CSRF validation failed", status_code=403, media_type="text/plain"
                )

        response = await call_next(request)
        if set_cookie:
            response.set_cookie(
                CSRF_COOKIE,
                cookie_value,
                httponly=False,  # JS must read it to set the header
                secure=request.url.scheme == "https",
                samesite="lax",
                path="/",
            )
        return response
