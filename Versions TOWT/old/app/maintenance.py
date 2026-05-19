"""
Maintenance mode middleware.

When enabled via admin settings, blocks all access except:
- /login (so admin can log in)
- /admin/settings (so admin can disable it)
- /static/* (CSS/JS/images)
- Admin users (role = administrateur) can still access everything

Controlled by a simple file flag: /app/data/maintenance.flag
When this file exists, maintenance mode is ON.
"""

import os
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import HTMLResponse
from fastapi import Request

MAINTENANCE_FLAG = "/app/data/maintenance.flag"
# Fallback for local dev
MAINTENANCE_FLAG_LOCAL = "maintenance.flag"


def is_maintenance_mode() -> bool:
    """Check if maintenance mode is currently active."""
    return os.path.exists(MAINTENANCE_FLAG) or os.path.exists(MAINTENANCE_FLAG_LOCAL)


def enable_maintenance(message: str = ""):
    """Enable maintenance mode."""
    flag_path = MAINTENANCE_FLAG if os.path.isdir("/app/data") else MAINTENANCE_FLAG_LOCAL
    os.makedirs(os.path.dirname(flag_path) if os.path.dirname(flag_path) else ".", exist_ok=True)
    with open(flag_path, "w") as f:
        f.write(message or "Mise a jour en cours")


def disable_maintenance():
    """Disable maintenance mode."""
    for path in [MAINTENANCE_FLAG, MAINTENANCE_FLAG_LOCAL]:
        if os.path.exists(path):
            os.remove(path)


def get_maintenance_message() -> str:
    """Get the maintenance message."""
    for path in [MAINTENANCE_FLAG, MAINTENANCE_FLAG_LOCAL]:
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    return f.read().strip() or "Mise a jour en cours"
            except Exception:
                return "Mise a jour en cours"
    return ""


# Paths that bypass maintenance mode
BYPASS_PATHS = ["/login", "/logout", "/admin/settings", "/admin/maintenance", "/static/"]

MAINTENANCE_HTML = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Maintenance — TOWT</title>
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap" rel="stylesheet">
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: 'Poppins', system-ui, sans-serif; background: #f0f4f8; display: flex; align-items: center; justify-content: center; min-height: 100vh; }
.card { background: white; border-radius: 16px; box-shadow: 0 4px 24px rgba(0,0,0,0.1); padding: 48px; max-width: 500px; text-align: center; }
.icon { font-size: 48px; margin-bottom: 16px; }
h1 { color: #1a3a5c; font-size: 1.5rem; margin-bottom: 8px; }
p { color: #6c757d; font-size: 0.95rem; line-height: 1.6; margin-bottom: 16px; }
.brand { color: #87BD2B; font-weight: 700; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 2px; }
</style>
</head>
<body>
<div class="card">
<div class="icon">&#9881;</div>
<h1>Maintenance en cours</h1>
<p>{message}</p>
<p style="font-size:0.85rem;">L'application sera de retour dans quelques instants.</p>
<div class="brand">TOWT — Transport a la Voile</div>
</div>
</body>
</html>"""


class MaintenanceMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not is_maintenance_mode():
            return await call_next(request)

        path = request.url.path

        # Always allow bypass paths
        for bp in BYPASS_PATHS:
            if path.startswith(bp):
                return await call_next(request)

        # Allow admin users through (check session cookie directly)
        try:
            from app.auth import serializer, COOKIE_NAME
            from app.database import async_session
            from app.models.user import User
            from sqlalchemy import select as sa_select
            token = request.cookies.get(COOKIE_NAME)
            if token:
                data = serializer.loads(token, max_age=86400 * 7)
                async with async_session() as db:
                    result = await db.execute(
                        sa_select(User).where(User.id == data["user_id"], User.is_active == True)
                    )
                    user = result.scalar_one_or_none()
                    if user and getattr(user, 'role', '') in ('administrateur', 'admin'):
                        return await call_next(request)
        except Exception:
            pass

        # Block everyone else
        message = get_maintenance_message()
        html = MAINTENANCE_HTML.replace("{message}", message)
        return HTMLResponse(content=html, status_code=503)
