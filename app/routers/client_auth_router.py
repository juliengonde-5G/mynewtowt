"""Client authentication — login, register, logout, change password.

Separate cookie / serializer from staff (`towt_client_session`).

Hardenings V3.1 :
  - Login : rate-limit persistant (`rate_limit_attempts`), 10 tentatives /
    10 min / IP → 429.
  - Anti-énumération : message d'erreur unique + bcrypt fictif sur email
    inexistant pour égaliser le temps de réponse.
  - Pas de PII en clair dans les logs (email hashé côté ``activity.record``).
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import (
    cookie_kwargs_for_client,
    create_client_session,
    hash_password,
    verify_password,
    CLIENT_COOKIE,
)
from app.database import get_db
from app.models.client_account import ClientAccount
from app.services import rate_limit
from app.services.activity import record as activity_record
from app.templating import templates


# Hash bcrypt fictif (vrai bcrypt cost=12) utilisé pour égaliser le temps
# quand l'email n'existe pas — précalculé pour le password aléatoire
# "newtowt_decoy_password_2026" (valeur jamais utilisée en clair).
# Évite de calculer un hash au module-load (incompatibilité bcrypt v4 +
# passlib < 1.8 sur certains envs).
_DUMMY_HASH = "$2b$12$O/jKlBtKnLgWqyXmEjPq8eYDQ.UQ0Ahnt0LeG6h2XdNJgI4r5kSDS"

# Message d'erreur unique (anti-énum)
_LOGIN_ERR = "Identifiants incorrects ou compte non vérifié."

router = APIRouter(tags=["client-auth"])


@router.get("/me/login", response_class=HTMLResponse)
async def login_form(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "client/login.html", {"request": request, "error": None}
    )


@router.post("/me/login", response_class=HTMLResponse)
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    ip = _client_ip(request) or "unknown"
    email_clean = email.strip().lower()

    # Rate-limit par IP (10/10 min). On vérifie AVANT le lookup DB pour ne
    # pas exposer un canal de timing par cache miss.
    if await rate_limit.exceeded(
        db, scope="client_login_ip", identifier=ip,
        max_attempts=10, window_minutes=10,
    ):
        return templates.TemplateResponse(
            "client/login.html",
            {"request": request, "error": "Trop de tentatives — patientez 10 minutes."},
            status_code=429,
        )

    user = (
        await db.execute(
            select(ClientAccount).where(ClientAccount.email == email_clean)
        )
    ).scalar_one_or_none()

    # Anti-énum : on calcule TOUJOURS un verify_password, même si l'email
    # est inconnu (avec un hash fictif). Le temps de réponse est égalisé.
    if user is not None:
        ok = verify_password(password, user.hashed_password)
        verified = user.is_verified
    else:
        verify_password(password, _DUMMY_HASH)  # constant-time decoy
        ok = False
        verified = False

    if not ok or not verified:
        await rate_limit.record(db, scope="client_login_ip", identifier=ip)
        await activity_record(
            db,
            action="client_login_fail",
            module="booking",
            entity_type="client_account",
            entity_label=email_clean,  # automatiquement scrubbé par activity.record
            ip_address=ip,
        )
        # Petit jitter constant pour brouiller l'inférence
        await asyncio.sleep(0.05)
        return templates.TemplateResponse(
            "client/login.html",
            {"request": request, "error": _LOGIN_ERR},
            status_code=400,
        )

    user.last_login_at = datetime.now(timezone.utc)
    await activity_record(
        db,
        action="client_login",
        user_name=user.email,
        module="booking",
        entity_type="client_account",
        entity_id=user.id,
        ip_address=ip,
    )

    token = create_client_session(user.id)
    redirect = RedirectResponse(url="/me", status_code=303)
    redirect.set_cookie(value=token, **cookie_kwargs_for_client(request))
    return redirect


@router.get("/me/register", response_class=HTMLResponse)
async def register_form(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "client/register.html", {"request": request, "error": None}
    )


@router.post("/me/register", response_class=HTMLResponse)
async def register(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    company_name: str = Form(...),
    contact_name: str = Form(""),
    country: str = Form(""),
    db: AsyncSession = Depends(get_db),
):
    email_clean = email.strip().lower()
    if len(password) < 12:
        return templates.TemplateResponse(
            "client/register.html",
            {
                "request": request,
                "error": "Le mot de passe doit contenir au moins 12 caractères.",
            },
            status_code=400,
        )
    existing = (
        await db.execute(
            select(ClientAccount).where(ClientAccount.email == email_clean)
        )
    ).scalar_one_or_none()
    if existing:
        return templates.TemplateResponse(
            "client/register.html",
            {"request": request, "error": "Un compte existe déjà avec cet email."},
            status_code=400,
        )

    client = ClientAccount(
        email=email_clean,
        hashed_password=hash_password(password),
        company_name=company_name.strip(),
        contact_name=contact_name.strip() or None,
        country=(country.strip().upper() or None),
        # V3.0: instant verification for ease of testing; production should
        # require email-link verification before is_verified=True.
        is_verified=True,
        segment="occasional",
    )
    db.add(client)
    await db.flush()

    await activity_record(
        db,
        action="client_register",
        user_name=client.email,
        module="booking",
        entity_type="client_account",
        entity_id=client.id,
        entity_label=client.company_name,
        ip_address=_client_ip(request),
    )

    token = create_client_session(client.id)
    redirect = RedirectResponse(url="/me", status_code=303)
    redirect.set_cookie(value=token, **cookie_kwargs_for_client(request))
    return redirect


@router.get("/me/logout")
async def logout(request: Request) -> RedirectResponse:
    redirect = RedirectResponse(url="/", status_code=303)
    redirect.delete_cookie(CLIENT_COOKIE, path="/")
    return redirect


def _client_ip(request: Request) -> str | None:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else None
