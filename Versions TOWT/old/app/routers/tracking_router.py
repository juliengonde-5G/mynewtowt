"""Tracking API — receives satcom CSV files and stores vessel positions."""
import secrets
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Query, Request, Header
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload
from sqlalchemy.dialects.postgresql import insert as pg_insert
from datetime import datetime, timezone
from typing import Optional
import csv
import io
import re

from app.auth import get_current_user
from app.config import get_settings
from app.database import get_db
from app.models.user import User
from app.models.vessel import Vessel
from app.models.leg import Leg
from app.models.vessel_position import VesselPosition
from app.permissions import require_permission

router = APIRouter(prefix="/api/tracking", tags=["tracking"])


def require_tracking_token(x_api_token: Optional[str] = Header(None)) -> None:
    """Shared secret authentication for ingest endpoints.

    The token is compared with ``Settings.TRACKING_API_TOKEN`` via
    ``secrets.compare_digest`` to avoid timing leaks. The server refuses
    authentication when the configured token is empty — that way a
    misconfigured deployment fails closed instead of silently accepting
    every request.
    """
    expected = get_settings().TRACKING_API_TOKEN
    if not expected:
        raise HTTPException(
            status_code=503,
            detail="Tracking API not configured (TRACKING_API_TOKEN missing).",
        )
    if not x_api_token or not secrets.compare_digest(x_api_token, expected):
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Token")


# ─── HAVERSINE DISTANCE ────────────────────────────────────
import math

def haversine_nm(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Haversine distance in nautical miles between two GPS points."""
    R_NM = 3440.065  # Earth radius in NM
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return R_NM * 2 * math.asin(math.sqrt(a))


def _parse_csv(content: str) -> list[dict]:
    """Parse a satcom CSV (semicolon-separated) into a list of position dicts."""
    reader = csv.DictReader(io.StringIO(content), delimiter=";")
    positions = []
    for row in reader:
        try:
            date_str = row.get("Date", "").strip()
            if not date_str:
                continue
            # Parse ISO datetime, add UTC timezone if naive
            dt = datetime.fromisoformat(date_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)

            lat = float(row.get("Latitude", "0").strip())
            lon = float(row.get("Longitude", "0").strip())

            # SOG and COG can be empty
            sog_str = row.get("SOG (knots)", "").strip()
            cog_str = row.get("COG (degree)", "").strip()
            sog = float(sog_str) if sog_str else None
            cog = float(cog_str) if cog_str else None

            source = row.get("Active interface", "").strip() or None

            positions.append({
                "recorded_at": dt,
                "latitude": lat,
                "longitude": lon,
                "sog": sog,
                "cog": cog,
                "source": source,
            })
        except (ValueError, KeyError):
            continue  # skip malformed rows

    return positions


def _extract_vessel_name(filename: str) -> str:
    """Extract vessel name from filename like '20260226090502-anemos-satcoms.csv'."""
    # Remove timestamp prefix and -satcoms.csv suffix
    name = filename.lower()
    # Remove date prefix (digits and dashes at start)
    name = re.sub(r"^\d{14}-?", "", name)
    # Remove -satcoms.csv or similar suffix
    name = re.sub(r"-?satcoms.*$", "", name)
    # Clean up
    name = name.strip("-_ ")
    return name


async def _match_leg(db: AsyncSession, vessel_id: int, dt: datetime) -> Optional[int]:
    """Find the leg this position belongs to, based on dates."""
    # Priority 1: ATD <= dt <= ATA (actual dates)
    result = await db.execute(
        select(Leg.id).where(
            Leg.vessel_id == vessel_id,
            Leg.atd != None,
            Leg.atd <= dt,
            or_(Leg.ata == None, Leg.ata >= dt),
        ).order_by(Leg.atd.desc()).limit(1)
    )
    leg_id = result.scalar_one_or_none()
    if leg_id:
        return leg_id

    # Priority 2: ETD <= dt <= ETA (estimated dates)
    result = await db.execute(
        select(Leg.id).where(
            Leg.vessel_id == vessel_id,
            Leg.etd != None,
            Leg.etd <= dt,
            or_(Leg.eta == None, Leg.eta >= dt),
        ).order_by(Leg.etd.desc()).limit(1)
    )
    leg_id = result.scalar_one_or_none()
    if leg_id:
        return leg_id

    # Priority 3: nearest leg before this date (position during port stay after a leg)
    result = await db.execute(
        select(Leg.id).where(
            Leg.vessel_id == vessel_id,
            or_(Leg.ata != None, Leg.eta != None),
            or_(
                and_(Leg.ata != None, Leg.ata <= dt),
                and_(Leg.ata == None, Leg.eta != None, Leg.eta <= dt),
            ),
        ).order_by(Leg.ata.desc().nullslast(), Leg.eta.desc().nullslast()).limit(1)
    )
    return result.scalar_one_or_none()


@router.post("/upload", dependencies=[Depends(require_tracking_token)])
async def upload_tracking_csv(
    file: UploadFile = File(...),
    vessel_name: Optional[str] = Query(None, description="Override vessel name (otherwise extracted from filename)"),
    db: AsyncSession = Depends(get_db),
    user=Depends(require_permission("captain", "M")),
):
    """
    Upload a satcom CSV file with vessel positions.
    
    The vessel is identified from the filename (e.g. '20260226-anemos-satcoms.csv' → 'anemos').
    You can override with ?vessel_name=anemos.
    
    Duplicate positions (same vessel + same timestamp) are silently skipped.
    Each position is automatically matched to the active leg based on dates.
    """
    if not file.filename:
        raise HTTPException(400, "No filename provided")

    # Read content
    raw = await file.read()
    try:
        content = raw.decode("utf-8")
    except UnicodeDecodeError:
        content = raw.decode("latin-1")

    # Determine vessel
    v_name = vessel_name or _extract_vessel_name(file.filename)
    if not v_name:
        raise HTTPException(400, f"Cannot determine vessel name from filename '{file.filename}'. Use ?vessel_name=xxx")

    # Find vessel in DB (case-insensitive)
    result = await db.execute(
        select(Vessel).where(Vessel.name.ilike(f"%{v_name}%"))
    )
    vessel = result.scalar_one_or_none()
    if not vessel:
        raise HTTPException(404, f"Vessel '{v_name}' not found in database")

    # Parse CSV
    positions = _parse_csv(content)
    if not positions:
        raise HTTPException(400, "No valid positions found in CSV")

    # Match legs and insert (skip duplicates)
    inserted = 0
    skipped = 0
    leg_cache = {}  # cache leg matching per date range

    for pos in positions:
        # Leg matching (cache by hour to reduce queries)
        cache_key = pos["recorded_at"].strftime("%Y-%m-%d-%H")
        if cache_key not in leg_cache:
            leg_cache[cache_key] = await _match_leg(db, vessel.id, pos["recorded_at"])
        leg_id = leg_cache[cache_key]

        # Upsert: insert or skip on conflict
        stmt = pg_insert(VesselPosition).values(
            vessel_id=vessel.id,
            leg_id=leg_id,
            latitude=pos["latitude"],
            longitude=pos["longitude"],
            sog=pos["sog"],
            cog=pos["cog"],
            recorded_at=pos["recorded_at"],
            source=pos["source"],
            import_batch=file.filename,
        ).on_conflict_do_nothing(
            constraint="uq_vessel_position_time"
        )
        result = await db.execute(stmt)
        if result.rowcount > 0:
            inserted += 1
        else:
            skipped += 1

    await db.flush()

    return JSONResponse({
        "status": "ok",
        "vessel": vessel.name,
        "vessel_id": vessel.id,
        "filename": file.filename,
        "total_points": len(positions),
        "inserted": inserted,
        "skipped_duplicates": skipped,
        "date_range": {
            "from": min(p["recorded_at"] for p in positions).isoformat(),
            "to": max(p["recorded_at"] for p in positions).isoformat(),
        } if positions else None,
    })


@router.get("/positions/{vessel_id}")
async def get_positions(
    vessel_id: int,
    leg_id: Optional[int] = Query(None),
    limit: int = Query(500, le=5000),
    db: AsyncSession = Depends(get_db),
    user=Depends(require_permission("captain", "C")),
):
    """Get recent positions for a vessel, optionally filtered by leg."""
    q = select(VesselPosition).where(VesselPosition.vessel_id == vessel_id)
    if leg_id:
        q = q.where(VesselPosition.leg_id == leg_id)
    q = q.order_by(VesselPosition.recorded_at.desc()).limit(limit)

    result = await db.execute(q)
    positions = result.scalars().all()

    return [{
        "id": p.id,
        "lat": p.latitude,
        "lon": p.longitude,
        "sog": p.sog,
        "cog": p.cog,
        "recorded_at": p.recorded_at.isoformat() if p.recorded_at else None,
        "leg_id": p.leg_id,
        "source": p.source,
    } for p in positions]


@router.get("/latest")
async def get_latest_positions(
    db: AsyncSession = Depends(get_db),
    user=Depends(require_permission("captain", "C")),
):
    """Get the most recent position for each active vessel."""
    # Subquery: max recorded_at per vessel
    from sqlalchemy import func
    subq = (
        select(
            VesselPosition.vessel_id,
            func.max(VesselPosition.recorded_at).label("max_time"),
        )
        .group_by(VesselPosition.vessel_id)
        .subquery()
    )

    result = await db.execute(
        select(VesselPosition)
        .options(selectinload(VesselPosition.vessel))
        .join(subq, and_(
            VesselPosition.vessel_id == subq.c.vessel_id,
            VesselPosition.recorded_at == subq.c.max_time,
        ))
    )
    positions = result.scalars().all()

    return [{
        "vessel_id": p.vessel_id,
        "vessel_name": p.vessel.name if p.vessel else None,
        "lat": p.latitude,
        "lon": p.longitude,
        "sog": p.sog,
        "cog": p.cog,
        "recorded_at": p.recorded_at.isoformat() if p.recorded_at else None,
        "leg_id": p.leg_id,
    } for p in positions]


@router.get("/leg/{leg_id}/track")
async def get_leg_track(
    leg_id: int,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_permission("captain", "C")),
):
    """
    Get full GPS track for a leg with computed navigation KPIs:
    - GPS distance (haversine sum)
    - Average/max SOG
    - Speed-colored segments for polyline rendering
    """
    # Get leg info
    leg_result = await db.execute(
        select(Leg).options(
            selectinload(Leg.vessel),
            selectinload(Leg.departure_port),
            selectinload(Leg.arrival_port),
        ).where(Leg.id == leg_id)
    )
    leg = leg_result.scalar_one_or_none()
    if not leg:
        raise HTTPException(404, f"Leg {leg_id} not found")

    # Get positions ordered chronologically
    result = await db.execute(
        select(VesselPosition)
        .where(VesselPosition.leg_id == leg_id)
        .order_by(VesselPosition.recorded_at.asc())
    )
    positions = result.scalars().all()

    if not positions:
        return {
            "leg_id": leg_id,
            "leg_code": leg.leg_code,
            "vessel": leg.vessel.name if leg.vessel else None,
            "route": f"{leg.departure_port.locode if leg.departure_port else '?'} → {leg.arrival_port.locode if leg.arrival_port else '?'}",
            "points": [],
            "gps_distance_nm": 0,
            "orthodromic_distance_nm": leg.distance_nm or 0,
            "computed_distance_nm": leg.computed_distance or 0,
            "avg_sog": 0,
            "max_sog": 0,
            "point_count": 0,
        }

    # Compute haversine distance and stats
    total_distance = 0.0
    sog_values = []
    points = []

    for i, p in enumerate(positions):
        if i > 0:
            prev = positions[i - 1]
            seg_dist = haversine_nm(prev.latitude, prev.longitude, p.latitude, p.longitude)
            # Skip unrealistic jumps (> 50 NM in 5 min = 600 kn)
            if seg_dist < 50:
                total_distance += seg_dist

        if p.sog is not None:
            sog_values.append(p.sog)

        points.append({
            "lat": p.latitude,
            "lon": p.longitude,
            "sog": p.sog,
            "cog": p.cog,
            "recorded_at": p.recorded_at.isoformat() if p.recorded_at else None,
        })

    avg_sog = round(sum(sog_values) / len(sog_values), 1) if sog_values else 0
    max_sog = round(max(sog_values), 1) if sog_values else 0

    # Elongation ratio: GPS distance / orthodromic distance
    ortho = leg.distance_nm or 0
    real_elongation = round(total_distance / ortho, 2) if ortho > 0 else None

    return {
        "leg_id": leg_id,
        "leg_code": leg.leg_code,
        "vessel": leg.vessel.name if leg.vessel else None,
        "route": f"{leg.departure_port.locode if leg.departure_port else '?'} → {leg.arrival_port.locode if leg.arrival_port else '?'}",
        "points": points,
        "gps_distance_nm": round(total_distance, 1),
        "orthodromic_distance_nm": ortho,
        "computed_distance_nm": leg.computed_distance or 0,
        "real_elongation": real_elongation,
        "avg_sog": avg_sog,
        "max_sog": max_sog,
        "point_count": len(points),
        "date_range": {
            "from": positions[0].recorded_at.isoformat(),
            "to": positions[-1].recorded_at.isoformat(),
        },
    }


@router.get("/navigation-kpis")
async def get_navigation_kpis(
    year: Optional[int] = Query(None),
    vessel_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    user=Depends(require_permission("kpi", "C")),
):
    """
    Get navigation KPIs for all legs that have GPS data.
    Returns per-leg: GPS distance, avg SOG, point count, etc.
    """
    from sqlalchemy import func as sqlfunc

    current_year = year or datetime.now(timezone.utc).year

    # Subquery: legs with GPS data + stats
    pos_stats = (
        select(
            VesselPosition.leg_id,
            sqlfunc.count(VesselPosition.id).label("point_count"),
            sqlfunc.avg(VesselPosition.sog).label("avg_sog"),
            sqlfunc.max(VesselPosition.sog).label("max_sog"),
            sqlfunc.min(VesselPosition.recorded_at).label("first_pos"),
            sqlfunc.max(VesselPosition.recorded_at).label("last_pos"),
        )
        .where(VesselPosition.leg_id != None)
        .group_by(VesselPosition.leg_id)
        .subquery()
    )

    query = (
        select(Leg, pos_stats)
        .join(pos_stats, Leg.id == pos_stats.c.leg_id)
        .options(
            selectinload(Leg.vessel),
            selectinload(Leg.departure_port),
            selectinload(Leg.arrival_port),
        )
        .where(Leg.year == current_year)
    )
    if vessel_id:
        query = query.where(Leg.vessel_id == vessel_id)

    result = await db.execute(query.order_by(Leg.vessel_id, Leg.sequence))
    rows = result.all()

    legs_data = []
    for row in rows:
        leg = row[0]
        legs_data.append({
            "leg_id": leg.id,
            "leg_code": leg.leg_code,
            "vessel": leg.vessel.name if leg.vessel else None,
            "vessel_id": leg.vessel_id,
            "route": f"{leg.departure_port.locode if leg.departure_port else '?'} → {leg.arrival_port.locode if leg.arrival_port else '?'}",
            "orthodromic_nm": leg.distance_nm or 0,
            "computed_nm": leg.computed_distance or 0,
            "point_count": row.point_count,
            "avg_sog": round(float(row.avg_sog or 0), 1),
            "max_sog": round(float(row.max_sog or 0), 1),
            "first_pos": row.first_pos.isoformat() if row.first_pos else None,
            "last_pos": row.last_pos.isoformat() if row.last_pos else None,
        })

    return {"year": current_year, "legs": legs_data}
