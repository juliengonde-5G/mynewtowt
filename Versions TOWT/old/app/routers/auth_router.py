import logging
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from app.templating import templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.user import User
from app.auth import verify_password, create_session_token, COOKIE_NAME
from app.services import rate_limit as rl
from app.utils.activity import log_activity, get_client_ip

logger = logging.getLogger(__name__)

router = APIRouter(tags=["auth"])

# ── Rate limiting for login (persisted in DB — A2.5) ─────────
_RL_SCOPE = "login"
LOGIN_RATE_LIMIT = 5          # max failed attempts
LOGIN_RATE_WINDOW = 300       # per 5 minutes (matches former lockout window)


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("auth/login.html", {
        "request": request,
        "error": None,
    })


@router.post("/login", response_class=HTMLResponse)
async def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    ip = get_client_ip(request)

    # Rate limiting check (DB-backed since Sprint 2 — A2.5)
    if await rl.is_rate_limited(db, _RL_SCOPE, ip, LOGIN_RATE_LIMIT, LOGIN_RATE_WINDOW):
        logger.warning(f"Login rate limited for IP {ip}")
        return templates.TemplateResponse("auth/login.html", {
            "request": request,
            "error": "Trop de tentatives de connexion. Veuillez réessayer dans quelques minutes.",
        }, status_code=429)

    # Truncate input to prevent abuse
    username = username[:50]
    password = password[:128]

    # Find user
    result = await db.execute(
        select(User).where(User.username == username, User.is_active == True)
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(password, user.hashed_password):
        await rl.record_attempt(db, _RL_SCOPE, ip)
        # Log failed login
        await log_activity(db, action="login_fail", module="auth",
                           detail=f"username: {username}", ip_address=ip)
        await db.flush()
        return templates.TemplateResponse("auth/login.html", {
            "request": request,
            "error": "Identifiant ou mot de passe incorrect",
        })

    # Success — clear any past failed attempts for this IP
    await rl.clear_attempts(db, _RL_SCOPE, ip)

    # Log successful login
    await log_activity(db, user=user, action="login", module="auth",
                       entity_type="user", entity_id=user.id,
                       entity_label=user.full_name, ip_address=ip)
    await db.flush()

    # Create session
    token = create_session_token(user.id)
    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=True,
        max_age=60 * 60 * 8,  # 8 hours
        samesite="lax",
    )
    return response


@router.get("/logout")
async def logout(request: Request, db: AsyncSession = Depends(get_db)):
    # Try to log the logout
    from app.auth import get_current_user_optional
    try:
        user = await get_current_user_optional(request, db)
        if user:
            await log_activity(db, user=user, action="logout", module="auth",
                               entity_type="user", entity_id=user.id,
                               entity_label=user.full_name,
                               ip_address=get_client_ip(request))
            await db.flush()
    except Exception:
        pass
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(COOKIE_NAME)
    return response
