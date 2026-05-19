"""Public (no-auth) route for shared commercial planning links."""
import time
from collections import defaultdict
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from datetime import datetime, timezone as tz

from app.database import get_db
from app.templating import templates
from app.models.leg import Leg
from app.models.vessel import Vessel
from app.models.port import Port
from app.models.planning_share import PlanningShare
from app.utils.activity import get_client_ip

ext_router = APIRouter(prefix="/planning/share", tags=["planning-external"])


# S18: rate limit per IP against token brute-forcing.
# 20 hits / 60s window, 5-minute lockout on exceed.
_share_attempts: dict[str, list[float]] = defaultdict(list)
_SHARE_RATE_LIMIT = 20
_SHARE_RATE_WINDOW = 60
_SHARE_LOCKOUT = 300


def _check_share_rate_limit(ip: str) -> bool:
    now = time.time()
    _share_attempts[ip] = [t for t in _share_attempts[ip] if now - t < _SHARE_LOCKOUT]
    recent = [t for t in _share_attempts[ip] if now - t < _SHARE_RATE_WINDOW]
    _share_attempts[ip].append(now)
    return len(recent) < _SHARE_RATE_LIMIT


@ext_router.get("/{token}", response_class=HTMLResponse)
async def view_shared_planning(
    request: Request,
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """Public view — always shows the latest planning data matching the saved filters."""
    if not _check_share_rate_limit(get_client_ip(request)):
        raise HTTPException(status_code=429, detail="Trop de requêtes, réessayer plus tard")
    result = await db.execute(
        select(PlanningShare).where(PlanningShare.token == token)
    )
    share = result.scalar_one_or_none()
    if not share:
        raise HTTPException(status_code=404, detail="Planning link not found")
    if not share.is_active:
        raise HTTPException(status_code=410, detail="This planning link has been deactivated")

    lang = share.lang or "fr"
    current_year = share.year

    # Load vessels for reference
    vessels_result = await db.execute(select(Vessel).where(Vessel.is_active == True).order_by(Vessel.code))
    vessels = vessels_result.scalars().all()

    # Build query with saved filters
    query = (
        select(Leg)
        .options(selectinload(Leg.vessel), selectinload(Leg.departure_port), selectinload(Leg.arrival_port))
        .where(Leg.year == current_year, Leg.status != "cancelled")
    )

    if share.vessel_code:
        v_result = await db.execute(select(Vessel).where(Vessel.code == share.vessel_code))
        v = v_result.scalar_one_or_none()
        if v:
            query = query.where(Leg.vessel_id == v.id)

    if share.destination_locode:
        query = query.where(Leg.arrival_port_locode == share.destination_locode)

    if share.origin_locode:
        query = query.where(Leg.departure_port_locode == share.origin_locode)

    result = await db.execute(query.order_by(Leg.etd.asc().nullslast(), Leg.vessel_id, Leg.sequence))
    legs = result.scalars().all()

    # If custom leg selection was saved, filter further
    selected_leg_ids = set()
    if share.legs_ids:
        selected_leg_ids = set(int(x) for x in share.legs_ids.split(",") if x.strip().isdigit())
        legs = [l for l in legs if l.id in selected_leg_ids]

    # Group by vessel
    legs_by_vessel = {}
    for leg in legs:
        vname = leg.vessel.name
        if vname not in legs_by_vessel:
            legs_by_vessel[vname] = []
        legs_by_vessel[vname].append(leg)

    # Group by route
    legs_by_route = {}
    for leg in legs:
        route = f"{leg.departure_port.name} → {leg.arrival_port.name}"
        if route not in legs_by_route:
            legs_by_route[route] = []
        legs_by_route[route].append(leg)

    # Group by destination
    legs_by_dest = {}
    for leg in legs:
        dest = leg.arrival_port.name
        if dest not in legs_by_dest:
            legs_by_dest[dest] = []
        legs_by_dest[dest].append(leg)

    # Build title
    title_parts = []
    if share.vessel_code:
        vname = next((v.name for v in vessels if v.code == share.vessel_code), "")
        title_parts.append(vname)
    if share.origin_locode:
        oname = share.origin_locode
        for leg in legs:
            if leg.departure_port_locode == share.origin_locode:
                oname = leg.departure_port.name
                break
        if lang == "en":
            title_parts.append(f"from {oname}")
        else:
            title_parts.append(f"au départ de {oname}")
    if share.destination_locode:
        dname = share.destination_locode
        for leg in legs:
            if leg.arrival_port_locode == share.destination_locode:
                dname = leg.arrival_port.name
                break
        if lang == "en":
            title_parts.append(f"to {dname}")
        else:
            title_parts.append(f"vers {dname}")

    if title_parts:
        prefix = "Sailing schedule" if lang == "en" else "Planning de navigation"
        title = f"{prefix} — {' · '.join(title_parts)}"
    else:
        title = "Sailing schedule — All departures" if lang == "en" else "Planning de navigation — Tous les départs"

    return templates.TemplateResponse("planning/pdf_commercial_shared.html", {
        "request": request,
        "title": title,
        "legs": legs,
        "legs_by_vessel": legs_by_vessel,
        "legs_by_route": legs_by_route,
        "legs_by_dest": legs_by_dest,
        "current_year": current_year,
        "lang": lang,
        "now": datetime.now(tz.utc),
        "share": share,
    })
