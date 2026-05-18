"""HTTP middlewares for mynewtowt."""

from app.middlewares.security_headers import SecurityHeadersMiddleware

__all__ = ["SecurityHeadersMiddleware"]
