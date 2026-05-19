import logging
import os
import stat

from pathlib import Path
from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, PlainTextResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from contextlib import asynccontextmanager

from app.config import get_settings
from app.database import init_db
from app.auth import AuthRequired
from app.routers.auth_router import router as auth_router
from app.routers.dashboard_router import router as dashboard_router
from app.routers.planning_router import router as planning_router
from app.routers.api_ports import router as api_ports_router
from app.routers.admin_router import router as admin_router
from app.routers.kpi_router import router as kpi_router
from app.routers.commercial_router import router as commercial_router
from app.routers.escale_router import router as escale_router
from app.routers.finance_router import router as finance_router
from app.routers.crew_router import router as crew_router
from app.routers.cargo_router import router as cargo_router, ext_router as cargo_ext_router
from app.routers.onboard_router import router as onboard_router
from app.routers.mrv_router import router as mrv_router
from app.routers.claim_router import router as claim_router
from app.routers.tracking_router import router as tracking_router
from app.routers.pricing_router import router as pricing_router
from app.routers.stowage_router import router as stowage_router
from app.routers.planning_ext_router import ext_router as planning_ext_router

logger = logging.getLogger(__name__)

settings = get_settings()


def _fix_static_permissions():
    """Fix file permissions on static and templates directories at startup to prevent 403."""
    for base_dir in ["app/static", "app/templates"]:
        if not os.path.isdir(base_dir):
            continue
        try:
            os.chmod(base_dir, os.stat(base_dir).st_mode | stat.S_IROTH | stat.S_IXOTH | stat.S_IRGRP | stat.S_IXGRP)
        except OSError:
            pass
        for root, dirs, files in os.walk(base_dir):
            for d in dirs:
                p = os.path.join(root, d)
                try:
                    os.chmod(p, os.stat(p).st_mode | stat.S_IROTH | stat.S_IXOTH | stat.S_IRGRP | stat.S_IXGRP)
                except OSError:
                    pass
            for f in files:
                p = os.path.join(root, f)
                try:
                    os.chmod(p, os.stat(p).st_mode | stat.S_IROTH | stat.S_IRGRP)
                except OSError:
                    pass


_DEFAULT_SECRET_KEY = "towt_secret_key_change_in_production_2025"
_DEFAULT_DB_PASSWORD = "towt_secure_2025"


def _validate_secrets():
    """Refuse to start in production when credentials are still default values.

    In non-production environments (APP_ENV != 'production'), emit a warning
    instead so local dev is not blocked.
    """
    findings = []
    if settings.SECRET_KEY == _DEFAULT_SECRET_KEY:
        findings.append(
            "SECRET_KEY is the default. "
            "Generate one with: python3 -c \"import secrets; print(secrets.token_hex(32))\""
        )
    if _DEFAULT_DB_PASSWORD in settings.DATABASE_URL:
        findings.append(
            "DATABASE_URL still contains the default Postgres password. "
            "Set POSTGRES_PASSWORD in .env and redeploy."
        )

    if not findings:
        return

    is_production = settings.APP_ENV == "production"
    message = (
        "Insecure default credentials detected:\n  - "
        + "\n  - ".join(findings)
    )
    if is_production:
        raise RuntimeError(
            "Refusing to start in production with default credentials.\n"
            + message
        )
    logger.warning("SECURITY WARNING: %s", message)


@asynccontextmanager
async def lifespan(app: FastAPI):
    _fix_static_permissions()
    _validate_secrets()
    await init_db()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
    redirect_slashes=False,
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

# ── CORS — restricted methods and headers ────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://my.towt.eu", "http://51.178.59.174"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With", "HX-Request",
                   "HX-Current-URL", "HX-Target", "HX-Trigger"],
)


# ── Security headers middleware ──────────────────────────────
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://unpkg.com; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: https://*.tile.openstreetmap.org; "
            "connect-src 'self' https://unpkg.com https://nominatim.openstreetmap.org; "
        )
        response.headers["Content-Security-Policy"] = csp
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response


app.add_middleware(SecurityHeadersMiddleware)

# ── Maintenance mode middleware ──────────────────────────────
from app.maintenance import MaintenanceMiddleware
app.add_middleware(MaintenanceMiddleware)

# ── CSRF middleware ──────────────────────────────────────────
from app.csrf import CSRFMiddleware
app.add_middleware(CSRFMiddleware)

# ── Force-change-password middleware ─────────────────────────
from app.security_middleware import ForcePasswordChangeMiddleware
app.add_middleware(ForcePasswordChangeMiddleware)


# ── Exception handlers ───────────────────────────────────────
@app.exception_handler(AuthRequired)
async def auth_required_handler(request: Request, exc: AuthRequired):
    return RedirectResponse(url="/login", status_code=303)


from starlette.exceptions import HTTPException as StarletteHTTPException

@app.exception_handler(403)
async def forbidden_handler(request: Request, exc):
    # Content negotiation: JSON for API clients, HTML for browsers
    accept = request.headers.get("accept", "")
    if "application/json" in accept:
        return JSONResponse({"detail": "Forbidden"}, status_code=403)

    from app.templating import templates
    return templates.TemplateResponse("403.html", {
        "request": request, "user": None,
        "active_module": "", "lang": "fr",
    }, status_code=403)


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    accept = request.headers.get("accept", "")
    if "application/json" in accept:
        return JSONResponse({"detail": "Not found"}, status_code=404)

    from app.templating import templates
    try:
        return templates.TemplateResponse("404.html", {
            "request": request, "user": None,
            "active_module": "", "lang": "fr",
        }, status_code=404)
    except Exception:
        return PlainTextResponse("Page non trouvée", status_code=404)


# ── Security.txt endpoint ────────────────────────────────────
@app.get("/.well-known/security.txt", response_class=PlainTextResponse)
async def security_txt():
    return (
        "Contact: security@towt.eu\n"
        "Expires: 2027-03-09T12:00:00.000Z\n"
        "Preferred-Languages: fr, en\n"
    )


# ── Internal docs (workflow diagram) — authenticated users only ──
from app.auth import get_current_user
_DOCS_DIR = Path(__file__).resolve().parent.parent / "docs"


@app.get("/internal/workflows", include_in_schema=False)
async def internal_workflows(user=Depends(get_current_user)):
    return FileResponse(_DOCS_DIR / "workflows.html", media_type="text/html")


@app.get("/internal/flows.json", include_in_schema=False)
async def internal_flows_json(user=Depends(get_current_user)):
    return FileResponse(_DOCS_DIR / "flows.json", media_type="application/json")


from app.permissions import require_permission

app.include_router(auth_router)
app.include_router(dashboard_router)
app.include_router(planning_router, dependencies=[Depends(require_permission("planning", "C"))])
app.include_router(api_ports_router)
from app.routers.admin_router import require_admin, account_router
app.include_router(admin_router, dependencies=[Depends(require_admin)])
app.include_router(account_router)
app.include_router(kpi_router, dependencies=[Depends(require_permission("kpi", "C"))])
app.include_router(commercial_router, dependencies=[Depends(require_permission("commercial", "C"))])
app.include_router(escale_router, dependencies=[Depends(require_permission("escale", "C"))])
app.include_router(finance_router, dependencies=[Depends(require_permission("finance", "C"))])
app.include_router(crew_router, dependencies=[Depends(require_permission("crew", "C"))])
app.include_router(cargo_router, dependencies=[Depends(require_permission("cargo", "C"))])
app.include_router(cargo_ext_router)
app.include_router(onboard_router, dependencies=[Depends(require_permission("captain", "C"))])
app.include_router(mrv_router, dependencies=[Depends(require_permission("mrv", "C"))])
app.include_router(claim_router, dependencies=[Depends(require_permission("captain", "C"))])
app.include_router(pricing_router, dependencies=[Depends(require_permission("commercial", "C"))])
app.include_router(stowage_router)  # Stowage plan — permissions enforced per endpoint
app.include_router(planning_ext_router)  # Public — shareable planning links (no auth)
app.include_router(tracking_router)  # API — no auth (called by Power Automate)
