from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.models.port import Port
from app.models.leg import Leg
from app.models.vessel import Vessel

router = APIRouter(prefix="/api/ports", tags=["api-ports"])


@router.get("/search")
async def search_ports(
    q: str = Query("", min_length=1),
    limit: int = Query(15, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Search ports by LOCODE or name for autocomplete."""
    search = f"%{q.upper()}%"
    result = await db.execute(
        select(Port)
        .where(
            or_(
                Port.locode.ilike(search),
                Port.name.ilike(f"%{q}%"),
            )
        )
        .order_by(Port.is_shortcut.desc(), Port.locode)
        .limit(limit)
    )
    ports = result.scalars().all()
    return JSONResponse([
        {
            "locode": p.locode,
            "name": p.name,
            "country_code": p.country_code,
            "latitude": p.latitude,
            "longitude": p.longitude,
            "is_shortcut": p.is_shortcut,
        }
        for p in ports
    ])


@router.get("/shortcuts")
async def shortcut_ports(db: AsyncSession = Depends(get_db)):
    """Get shortcut ports (Fécamp, São Sebastião)."""
    result = await db.execute(
        select(Port).where(Port.is_shortcut == True).order_by(Port.locode)
    )
    ports = result.scalars().all()
    return JSONResponse([
        {
            "locode": p.locode,
            "name": p.name,
            "country_code": p.country_code,
        }
        for p in ports
    ])


@router.get("/next-clocks")
async def next_port_clocks(db: AsyncSession = Depends(get_db)):
    """Return unique destination port timezones for vessels currently at sea."""
    from datetime import datetime, timezone
    from app.utils.timezones import get_port_timezone

    now = datetime.now(timezone.utc)
    current_year = now.year

    vessels_result = await db.execute(
        select(Vessel).where(Vessel.is_active == True)
    )
    vessels = vessels_result.scalars().all()

    seen_ports = set()
    clocks = []

    for v in vessels:
        legs_result = await db.execute(
            select(Leg).options(
                selectinload(Leg.arrival_port)
            ).where(Leg.vessel_id == v.id, Leg.year == current_year)
            .order_by(Leg.sequence)
        )
        legs = legs_result.scalars().all()

        # Find if vessel is at sea: has ATD but no ATA
        for leg in legs:
            if leg.atd and not leg.ata and leg.arrival_port:
                port = leg.arrival_port
                port_key = port.locode
                if port_key not in seen_ports:
                    seen_ports.add(port_key)
                    tz = get_port_timezone(port.country_code, port.zone_code)
                    clocks.append({
                        "port_name": port.name,
                        "timezone": tz,
                    })
                break

    return JSONResponse(clocks)
