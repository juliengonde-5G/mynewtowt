"""CSRF protection for forms.

Strategy: Double-submit cookie pattern.

- A random token is stored in a cookie (towt_csrf).
- Templates inject the token as a hidden field via ``{{ csrf_input() }}``.
- On POST/PUT/PATCH/DELETE the middleware validates the token by one of:
    * the ``x-csrf-token`` header (HTMX / AJAX), compared with the cookie
      via ``secrets.compare_digest``;
    * otherwise the ``csrf_token`` form field, parsed out of the body
      (``application/x-www-form-urlencoded`` or ``multipart/form-data``).
  The body is buffered and replayed to the downstream app so route
  handlers keep full access to ``request.form()`` / ``await file.read()``.
- JSON bodies without the header are rejected — there is no JSON-native
  form field to validate and those should always be HTMX/AJAX.
- External portal routes (``/p/``, ``/planning/ext/``), the login page
  and the tracking API are exempt.

Sprint 2 hardening (A2.1): added strict body-parsing for form POSTs so
we no longer rely solely on ``SameSite=Lax``.
"""
from __future__ import annotations

import logging
import secrets
from typing import Optional
from urllib.parse import parse_qs

from starlette.requests import Request
from fastapi.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

logger = logging.getLogger(__name__)

CSRF_COOKIE_NAME = "towt_csrf"
CSRF_FIELD_NAME = "csrf_token"
CSRF_HEADER_NAME = "x-csrf-token"
TOKEN_LENGTH = 32

# Routes excluded from CSRF validation (public/external portals + login)
CSRF_EXEMPT_PREFIXES = (
    "/p/",
    "/planning/ext/",
    "/api/",
    "/login",
    "/.well-known/",
)
SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}

# Max body size we are willing to buffer when validating a form CSRF token.
# File uploads above this threshold won't be CSRF-validated via the body
# (they still need the x-csrf-token header). Default is 10 MiB which is
# generous for the forms used here. Override via app.config if needed.
MAX_CSRF_BODY_BYTES = 10 * 1024 * 1024


def generate_csrf_token() -> str:
    return secrets.token_hex(TOKEN_LENGTH)


def csrf_input(request: Request) -> str:
    """Template helper: returns an HTML hidden input with the CSRF token."""
    token = request.cookies.get(CSRF_COOKIE_NAME, "")
    return f'<input type="hidden" name="{CSRF_FIELD_NAME}" value="{token}">'


async def _read_body(receive: Receive, limit: int) -> tuple[bytes, bool]:
    """Drain the receive stream up to ``limit`` bytes.

    Returns ``(body, truncated)``. When truncated is True we stopped
    reading, and the remainder is discarded — but we already know the
    request is too large for our CSRF buffer so the caller will reject it.
    """
    chunks: list[bytes] = []
    total = 0
    while True:
        message = await receive()
        if message["type"] == "http.disconnect":
            raise RuntimeError("client disconnected before CSRF validation")
        body = message.get("body", b"")
        total += len(body)
        if total > limit:
            return b"".join(chunks), True
        chunks.append(body)
        if not message.get("more_body", False):
            break
    return b"".join(chunks), False


def _make_replay_receive(body: bytes) -> Receive:
    """Return an ASGI ``receive`` coroutine that replays the buffered body once."""
    sent = False

    async def receive() -> dict:
        nonlocal sent
        if not sent:
            sent = True
            return {"type": "http.request", "body": body, "more_body": False}
        return {"type": "http.disconnect"}

    return receive


async def _extract_form_token(
    scope: Scope, body: bytes, content_type: str
) -> Optional[str]:
    """Pull the ``csrf_token`` field out of a POST body (urlencoded or multipart)."""
    if "application/x-www-form-urlencoded" in content_type:
        parsed = parse_qs(body.decode("utf-8", errors="replace"), keep_blank_values=True)
        values = parsed.get(CSRF_FIELD_NAME) or []
        return values[0] if values else None

    if "multipart/form-data" in content_type:
        # Delegate multipart parsing to Starlette, replaying the buffered body.
        temp_request = Request(scope, receive=_make_replay_receive(body))
        try:
            form = await temp_request.form()
        except Exception:
            return None
        val = form.get(CSRF_FIELD_NAME)
        if hasattr(val, "file"):
            # UploadFile — never valid for the token.
            return None
        return val

    # JSON / other content types: require the header.
    return None


def _forbid(scope: Scope, receive: Receive, send: Send, detail: str):
    response = JSONResponse({"detail": detail}, status_code=403)
    return response(scope, receive, send)


class CSRFMiddleware:
    """Pure ASGI middleware enforcing double-submit CSRF validation."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope)
        method = request.method
        csrf_cookie = request.cookies.get(CSRF_COOKIE_NAME)

        # Safe methods: ensure the cookie exists for future requests
        if method in SAFE_METHODS:
            if csrf_cookie:
                await self.app(scope, receive, send)
                return

            token = generate_csrf_token()
            cookie_set = False

            async def send_with_cookie(message):
                nonlocal cookie_set
                if message["type"] == "http.response.start" and not cookie_set:
                    cookie_set = True
                    headers = list(message.get("headers", []))
                    secure = "https" in str(scope.get("scheme", "http"))
                    cookie_val = (
                        f"{CSRF_COOKIE_NAME}={token}; Path=/; "
                        f"SameSite=Lax; Max-Age=28800"
                    )
                    if secure:
                        cookie_val += "; Secure"
                    headers.append((b"set-cookie", cookie_val.encode()))
                    message = {**message, "headers": headers}
                await send(message)

            await self.app(scope, receive, send_with_cookie)
            return

        # Unsafe methods: check exemptions first
        path = request.url.path
        if any(path.startswith(prefix) for prefix in CSRF_EXEMPT_PREFIXES):
            await self.app(scope, receive, send)
            return

        if not csrf_cookie:
            logger.warning("CSRF: missing cookie for %s %s", method, path)
            await _forbid(scope, receive, send, "CSRF token missing")
            return

        # 1. Header path — HTMX/AJAX. Body is untouched.
        header_token = request.headers.get(CSRF_HEADER_NAME)
        if header_token:
            if not secrets.compare_digest(header_token, csrf_cookie):
                logger.warning("CSRF: header token mismatch for %s %s", method, path)
                await _forbid(scope, receive, send, "CSRF validation failed")
                return
            await self.app(scope, receive, send)
            return

        # 2. Form path — buffer the body, pull csrf_token, replay body downstream.
        content_type = request.headers.get("content-type", "")
        try:
            body, truncated = await _read_body(receive, MAX_CSRF_BODY_BYTES)
        except RuntimeError:
            # Client disconnected mid-upload; nothing left to do.
            return

        if truncated:
            logger.warning(
                "CSRF: body over %d bytes for %s %s; must use x-csrf-token header",
                MAX_CSRF_BODY_BYTES,
                method,
                path,
            )
            await _forbid(scope, receive, send, "CSRF validation failed (body too large)")
            return

        form_token = await _extract_form_token(scope, body, content_type)
        if not form_token or not secrets.compare_digest(form_token, csrf_cookie):
            logger.warning("CSRF: form token missing/invalid for %s %s", method, path)
            await _forbid(scope, receive, send, "CSRF validation failed")
            return

        # Replay body for the downstream application.
        await self.app(scope, _make_replay_receive(body), send)
