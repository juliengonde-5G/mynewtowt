"""MRV (Monitoring, Reporting, Verification) fuel reporting router."""
import csv
import io
import math
from datetime import datetime, timezone, date, timedelta
from typing import Optional

from fastapi import APIRouter, Request, Depends, Form, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload

from app.templating import templates
from app.database import get_db
from app.auth import get_current_user
from app.models.user import User
from app.models.vessel import Vessel
from app.models.leg import Leg
from app.models.port import Port
from app.models.onboard import SofEvent, SOF_EVENT_TYPES
from app.utils.timezones import TIMEZONE_CHOICES
from app.models.mrv import MrvEvent, MrvParameter, MRV_EVENT_TYPES, MRV_DEFAULTS, SOF_TO_MRV_MAP
from app.models.vessel_position import VesselPosition
from app.utils.activity import log_activity
from app.permissions import can_edit

router = APIRouter(prefix="/mrv", tags=["mrv"])


# ═══════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════

def pf(val) -> Optional[float]:
    """Parse float from form value."""
    if val is None or str(val).strip() == "":
        return None
    try:
        return float(str(val).strip().replace(",", "."))
    except (ValueError, TypeError):
        return None


def pi(val) -> Optional[int]:
    """Parse int from form value."""
    if val is None or str(val).strip() == "":
        return None
    try:
        return int(float(str(val).strip().replace(",", ".")))
    except (ValueError, TypeError):
        return None


async def get_mrv_params(db: AsyncSession) -> dict:
    """Get MRV parameters from DB, fallback to defaults."""
    result = await db.execute(select(MrvParameter))
    stored = {p.parameter_name: p.parameter_value for p in result.scalars().all()}
    merged = {}
    for key, info in MRV_DEFAULTS.items():
        merged[key] = stored.get(key, info["value"])
    return merged


def compute_consumption(event: MrvEvent, prev_event: Optional[MrvEvent], density: float) -> dict:
    """Compute fuel consumption between two consecutive MRV events."""
    if not prev_event:
        return {"me": 0.0, "ae": 0.0, "total": 0.0}

    # Main Engine consumption = (port_me_delta + stbd_me_delta) * density
    port_me_delta = ((event.port_me_do_counter or 0) - (prev_event.port_me_do_counter or 0))
    stbd_me_delta = ((event.stbd_me_do_counter or 0) - (prev_event.stbd_me_do_counter or 0))
    me = (port_me_delta + stbd_me_delta) * density

    # Auxiliary Engine consumption = (fwd_gen_delta + aft_gen_delta) * density
    fwd_gen_delta = ((event.fwd_gen_do_counter or 0) - (prev_event.fwd_gen_do_counter or 0))
    aft_gen_delta = ((event.aft_gen_do_counter or 0) - (prev_event.aft_gen_do_counter or 0))
    ae = (fwd_gen_delta + aft_gen_delta) * density

    return {"me": round(me, 4), "ae": round(ae, 4), "total": round(me + ae, 4)}


def compute_rob(prev_event: Optional[MrvEvent], event: MrvEvent, consumption_total: float) -> float:
    """Calculate expected ROB: previous ROB + bunkering - consumption."""
    if not prev_event:
        return event.rob_mt or 0.0
    prev_rob = prev_event.rob_mt or 0.0
    bunkering = event.bunkering_qty_mt or 0.0
    return round(prev_rob + bunkering - consumption_total, 4)


def validate_quality(event: MrvEvent, prev_event: Optional[MrvEvent], params: dict) -> tuple:
    """
    Run quality checks on an MRV event.
    Returns (status, notes) where status is 'ok', 'warning', or 'error'.
    """
    notes = []
    status = "ok"

    if not prev_event:
        return ("ok", "First event - no comparison available")

    # Rule 1: DO Counters must be monotonically increasing
    counter_pairs = [
        ("port_me_do_counter", "Port ME"),
        ("stbd_me_do_counter", "Stbd ME"),
        ("fwd_gen_do_counter", "FWD Gen"),
        ("aft_gen_do_counter", "AFT Gen"),
    ]
    for field, label in counter_pairs:
        curr = getattr(event, field, None)
        prev = getattr(prev_event, field, None)
        if curr is not None and prev is not None and curr < prev:
            notes.append(f"ERREUR: Compteur {label} en baisse ({prev} → {curr})")
            status = "error"

    # Rule 2: ROB consistency
    if event.rob_mt is not None and event.rob_calculated is not None:
        deviation = abs(event.rob_mt - event.rob_calculated)
        admissible = params.get("mdo_admissible_deviation", 2.0)
        if deviation > admissible:
            notes.append(f"ERREUR: Déviation ROB {deviation:.2f}mt > seuil admissible {admissible}mt (déclaré: {event.rob_mt}, calculé: {event.rob_calculated:.2f})")
            status = "error"
        elif deviation > 0.5:
            notes.append(f"ALERTE: Déviation ROB {deviation:.2f}mt (déclaré: {event.rob_mt}, calculé: {event.rob_calculated:.2f})")
            if status != "error":
                status = "warning"

    # Rule 3: Cargo consistency within same trip (departure → arrival)
    if prev_event.cargo_mrv_mt is not None and event.cargo_mrv_mt is not None:
        if event.event_type in ("arrival", "begin_anchoring", "end_anchoring"):
            if abs(event.cargo_mrv_mt - prev_event.cargo_mrv_mt) > 0.1:
                notes.append(f"ALERTE: Cargo modifié en transit ({prev_event.cargo_mrv_mt} → {event.cargo_mrv_mt}mt)")
                if status != "error":
                    status = "warning"

    if not notes:
        notes.append("Contrôles qualité OK")

    return (status, " | ".join(notes))


async def recalculate_all_events(db: AsyncSession, leg_id: int, params: dict):
    """Recalculate consumption, ROB, and quality for all events in a leg."""
    result = await db.execute(
        select(MrvEvent).where(MrvEvent.leg_id == leg_id)
        .order_by(MrvEvent.timestamp_utc.asc(), MrvEvent.id.asc())
    )
    events = result.scalars().all()

    density = params.get("avg_mdo_density", 0.845)
    prev = None
    for evt in events:
        consumption = compute_consumption(evt, prev, density)
        evt.me_consumption_mdo = consumption["me"]
        evt.ae_consumption_mdo = consumption["ae"]
        evt.total_consumption_mdo = consumption["total"]
        evt.rob_calculated = compute_rob(prev, evt, consumption["total"])
        quality_status, quality_notes = validate_quality(evt, prev, params)
        evt.quality_status = quality_status
        evt.quality_notes = quality_notes
        prev = evt

    await db.flush()


def coords_from_port(port) -> dict:
    """Extract DMS coordinates from port lat/lon."""
    result = {}
    if port and port.latitude is not None:
        lat = port.latitude
        result["latitude_deg"] = int(abs(lat))
        result["latitude_min"] = int((abs(lat) - int(abs(lat))) * 60)
        result["latitude_ns"] = "N" if lat >= 0 else "S"
    if port and port.longitude is not None:
        lon = port.longitude
        result["longitude_deg"] = int(abs(lon))
        result["longitude_min"] = int((abs(lon) - int(abs(lon))) * 60)
        result["longitude_ew"] = "E" if lon >= 0 else "W"
    return result


def coords_from_decimal(lat: float, lon: float) -> dict:
    """Convert decimal lat/lon to DMS dict."""
    return {
        "latitude_deg": int(abs(lat)),
        "latitude_min": int((abs(lat) - int(abs(lat))) * 60),
        "latitude_ns": "N" if lat >= 0 else "S",
        "longitude_deg": int(abs(lon)),
        "longitude_min": int((abs(lon) - int(abs(lon))) * 60),
        "longitude_ew": "E" if lon >= 0 else "W",
    }


async def nearest_gps_position(db: AsyncSession, vessel_id: int, ts: datetime) -> Optional[dict]:
    """Find the VesselPosition closest to ts and return DMS coords, or None."""
    # Look for the closest position within +/- 6 hours of the event
    window = timedelta(hours=6)
    result = await db.execute(
        select(VesselPosition)
        .where(
            VesselPosition.vessel_id == vessel_id,
            VesselPosition.recorded_at >= ts - window,
            VesselPosition.recorded_at <= ts + window,
        )
        .order_by(func.abs(func.extract("epoch", VesselPosition.recorded_at - ts)))
        .limit(1)
    )
    pos = result.scalar_one_or_none()
    if pos and pos.latitude is not None and pos.longitude is not None:
        return coords_from_decimal(pos.latitude, pos.longitude)
    return None


# ═══════════════════════════════════════════════════════════════
#  MAIN PAGE — MRV Dashboard
# ═══════════════════════════════════════════════════════════════
@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def mrv_home(
    request: Request,
    vessel: Optional[int] = Query(None),
    year: Optional[int] = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_year = year or datetime.now().year
    years = list(range(2025, datetime.now().year + 2))

    vessels_result = await db.execute(
        select(Vessel).where(Vessel.is_active == True).order_by(Vessel.code)
    )
    vessels = vessels_result.scalars().all()

    selected_vessel = vessel or (vessels[0].code if vessels else None)
    vessel_obj = None
    if selected_vessel:
        v_result = await db.execute(select(Vessel).where(Vessel.code == selected_vessel))
        vessel_obj = v_result.scalar_one_or_none()

    legs_data = []
    summary = {"total_consumption": 0, "total_co2": 0, "events_count": 0,
               "quality_ok": 0, "quality_warning": 0, "quality_error": 0}
    params = await get_mrv_params(db)

    if vessel_obj:
        legs_result = await db.execute(
            select(Leg).options(
                selectinload(Leg.departure_port),
                selectinload(Leg.arrival_port),
            ).where(Leg.vessel_id == vessel_obj.id, Leg.year == current_year)
            .order_by(Leg.sequence)
        )
        legs = legs_result.scalars().all()

        for leg in legs:
            events_result = await db.execute(
                select(MrvEvent).where(MrvEvent.leg_id == leg.id)
                .order_by(MrvEvent.timestamp_utc.asc())
            )
            events = events_result.scalars().all()

            leg_consumption = sum(e.total_consumption_mdo or 0 for e in events)
            co2_factor = params.get("co2_emission_factor", 3.206)
            leg_co2 = leg_consumption * co2_factor

            quality_counts = {"ok": 0, "warning": 0, "error": 0, "pending": 0}
            for e in events:
                quality_counts[e.quality_status or "pending"] += 1

            legs_data.append({
                "leg": leg,
                "events_count": len(events),
                "consumption_mt": round(leg_consumption, 2),
                "co2_mt": round(leg_co2, 2),
                "quality": quality_counts,
                "worst_quality": "error" if quality_counts["error"] > 0
                    else "warning" if quality_counts["warning"] > 0
                    else "ok" if quality_counts["ok"] > 0
                    else "pending",
            })

            summary["total_consumption"] += leg_consumption
            summary["total_co2"] += leg_co2
            summary["events_count"] += len(events)
            summary["quality_ok"] += quality_counts["ok"]
            summary["quality_warning"] += quality_counts["warning"]
            summary["quality_error"] += quality_counts["error"]

    summary["total_consumption"] = round(summary["total_consumption"], 2)
    summary["total_co2"] = round(summary["total_co2"], 2)

    return templates.TemplateResponse("mrv/index.html", {
        "request": request, "user": user,
        "vessels": vessels, "selected_vessel": selected_vessel, "vessel_obj": vessel_obj,
        "current_year": current_year, "years": years,
        "legs_data": legs_data, "summary": summary, "params": params,
        "active_module": "mrv",
        "lang": user.language or "fr",
        "can_edit_mrv": can_edit(user, "mrv"),
    })


# ═══════════════════════════════════════════════════════════════
#  LEG DETAIL — MRV Events for a specific leg
# ═══════════════════════════════════════════════════════════════
@router.get("/leg/{leg_id}", response_class=HTMLResponse)
async def mrv_leg_detail(
    leg_id: int,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    leg_result = await db.execute(
        select(Leg).options(
            selectinload(Leg.vessel),
            selectinload(Leg.departure_port),
            selectinload(Leg.arrival_port),
        ).where(Leg.id == leg_id)
    )
    leg = leg_result.scalar_one_or_none()
    if not leg:
        raise HTTPException(404)

    # MRV Events
    events_result = await db.execute(
        select(MrvEvent).where(MrvEvent.leg_id == leg_id)
        .order_by(MrvEvent.timestamp_utc.asc(), MrvEvent.id.asc())
    )
    events = events_result.scalars().all()

    # SOF events for this leg (to show link)
    sof_result = await db.execute(
        select(SofEvent).where(SofEvent.leg_id == leg_id)
        .order_by(SofEvent.event_date.asc().nulls_last(), SofEvent.event_time.asc().nulls_last())
    )
    sof_events = sof_result.scalars().all()

    # Identify SOF events that map to MRV and are not yet linked
    linked_sof_ids = {e.sof_event_id for e in events if e.sof_event_id}
    sof_suggestions = []
    for sof in sof_events:
        if sof.id not in linked_sof_ids and sof.event_type in SOF_TO_MRV_MAP:
            sof_suggestions.append(sof)

    params = await get_mrv_params(db)
    co2_factor = params.get("co2_emission_factor", 3.206)

    total_consumption = sum(e.total_consumption_mdo or 0 for e in events)
    total_co2 = total_consumption * co2_factor

    # Quality summary
    quality_counts = {"ok": 0, "warning": 0, "error": 0, "pending": 0}
    for e in events:
        quality_counts[e.quality_status or "pending"] += 1

    return templates.TemplateResponse("mrv/leg_detail.html", {
        "request": request, "user": user,
        "leg": leg, "events": events,
        "sof_events": sof_events, "sof_suggestions": sof_suggestions,
        "mrv_event_types": MRV_EVENT_TYPES,
        "sof_to_mrv_map": SOF_TO_MRV_MAP,
        "params": params, "co2_factor": co2_factor,
        "total_consumption": round(total_consumption, 2),
        "total_co2": round(total_co2, 2),
        "quality_counts": quality_counts,
        "tz_choices": TIMEZONE_CHOICES,
        "active_module": "mrv",
        "lang": user.language or "fr",
        "can_edit_mrv": can_edit(user, "mrv"),
    })


# ═══════════════════════════════════════════════════════════════
#  CREATE MRV EVENT
# ═══════════════════════════════════════════════════════════════
@router.post("/events/add", response_class=HTMLResponse)
async def mrv_add_event(
    request: Request,
    leg_id: int = Form(...),
    event_type: str = Form(...),
    timestamp_date: str = Form(...),
    timestamp_time: str = Form("00:00"),
    port_me_do_counter: str = Form(""),
    stbd_me_do_counter: str = Form(""),
    fwd_gen_do_counter: str = Form(""),
    aft_gen_do_counter: str = Form(""),
    rob_mt: str = Form(""),
    cargo_mrv_mt: str = Form(""),
    bunkering_qty_mt: str = Form(""),
    bunkering_date: str = Form(""),
    latitude_deg: str = Form(""),
    latitude_min: str = Form(""),
    latitude_ns: str = Form("N"),
    longitude_deg: str = Form(""),
    longitude_min: str = Form(""),
    longitude_ew: str = Form("E"),
    distance_nm: str = Form(""),
    sof_event_id: str = Form(""),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.permissions import require_permission
    # Parse timestamp
    try:
        ts = datetime.strptime(f"{timestamp_date} {timestamp_time}", "%Y-%m-%d %H:%M")
        ts = ts.replace(tzinfo=timezone.utc)
    except ValueError:
        raise HTTPException(400, "Format date/heure invalide")

    # Auto-fill coordinates: port coords for departure/arrival, GPS history for others
    lat_d, lat_m, lon_d, lon_m = pi(latitude_deg), pi(latitude_min), pi(longitude_deg), pi(longitude_min)
    if lat_d is None:
        leg = await db.get(Leg, leg_id)
        coords = None
        if leg and event_type in ("departure", "arrival"):
            port_locode = leg.departure_port_locode if event_type == "departure" else leg.arrival_port_locode
            port_result = await db.execute(select(Port).where(Port.locode == port_locode))
            port = port_result.scalar_one_or_none()
            coords = coords_from_port(port)
        if not coords and leg:
            # Fallback: nearest GPS position from vessel tracking history
            coords = await nearest_gps_position(db, leg.vessel_id, ts)
        if coords:
            lat_d = coords.get("latitude_deg", lat_d)
            lat_m = coords.get("latitude_min", lat_m)
            latitude_ns = coords.get("latitude_ns", latitude_ns)
            lon_d = coords.get("longitude_deg", lon_d)
            lon_m = coords.get("longitude_min", lon_m)
            longitude_ew = coords.get("longitude_ew", longitude_ew)

    evt = MrvEvent(
        leg_id=leg_id,
        sof_event_id=pi(sof_event_id),
        event_type=event_type,
        timestamp_utc=ts,
        port_me_do_counter=pf(port_me_do_counter),
        stbd_me_do_counter=pf(stbd_me_do_counter),
        fwd_gen_do_counter=pf(fwd_gen_do_counter),
        aft_gen_do_counter=pf(aft_gen_do_counter),
        rob_mt=pf(rob_mt),
        cargo_mrv_mt=pf(cargo_mrv_mt),
        bunkering_qty_mt=pf(bunkering_qty_mt) if event_type == "departure" else None,
        bunkering_date=datetime.strptime(bunkering_date, "%Y-%m-%d").date() if bunkering_date and event_type == "departure" else None,
        latitude_deg=lat_d,
        latitude_min=lat_m,
        latitude_ns=latitude_ns if lat_d is not None else None,
        longitude_deg=lon_d,
        longitude_min=lon_m,
        longitude_ew=longitude_ew if lon_d is not None else None,
        distance_nm=pf(distance_nm),
        created_by=user.full_name,
    )
    db.add(evt)
    await db.flush()

    # Recalculate all events for this leg
    params = await get_mrv_params(db)
    await recalculate_all_events(db, leg_id, params)

    await log_activity(db, user, "mrv", "create", "MrvEvent", evt.id,
                       f"MRV {event_type} - Leg {leg_id}")

    return RedirectResponse(url=f"/mrv/leg/{leg_id}", status_code=303)


# ═══════════════════════════════════════════════════════════════
#  CREATE MRV EVENT FROM SOF
# ═══════════════════════════════════════════════════════════════
@router.post("/events/from-sof", response_class=HTMLResponse)
async def mrv_from_sof(
    request: Request,
    sof_event_id: int = Form(...),
    leg_id: int = Form(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create MRV event pre-filled from a SOF event."""
    sof = await db.get(SofEvent, sof_event_id)
    if not sof:
        raise HTTPException(404, "Événement SOF introuvable")

    mrv_type = SOF_TO_MRV_MAP.get(sof.event_type)
    if not mrv_type:
        raise HTTPException(400, f"Type SOF '{sof.event_type}' non mappable vers MRV")

    # Build timestamp from SOF date/time
    event_date = sof.event_date or date.today()
    event_time = sof.event_time or "00:00"
    try:
        ts = datetime.strptime(f"{event_date} {event_time}", "%Y-%m-%d %H:%M")
        ts = ts.replace(tzinfo=timezone.utc)
    except ValueError:
        ts = datetime.now(timezone.utc)

    # Auto-fill coordinates: port coords for departure/arrival, GPS history fallback
    leg = await db.get(Leg, leg_id)
    lat_d = lat_m = lon_d = lon_m = None
    lat_ns = "N"
    lon_ew = "E"
    coords = None
    if leg and mrv_type in ("departure", "arrival"):
        port_locode = leg.departure_port_locode if mrv_type == "departure" else leg.arrival_port_locode
        port_result = await db.execute(select(Port).where(Port.locode == port_locode))
        port = port_result.scalar_one_or_none()
        coords = coords_from_port(port)
    if not coords and leg:
        coords = await nearest_gps_position(db, leg.vessel_id, ts)
    if coords:
        lat_d = coords.get("latitude_deg")
        lat_m = coords.get("latitude_min")
        lat_ns = coords.get("latitude_ns", "N")
        lon_d = coords.get("longitude_deg")
        lon_m = coords.get("longitude_min")
        lon_ew = coords.get("longitude_ew", "E")

    # Distance: 0 for departure, leg distance for arrival
    dist = 0.0
    if mrv_type == "arrival" and leg:
        dist = leg.computed_distance or (leg.distance_nm * (leg.elongation_coeff or 1.25) if leg.distance_nm else 0)

    evt = MrvEvent(
        leg_id=leg_id,
        sof_event_id=sof_event_id,
        event_type=mrv_type,
        timestamp_utc=ts,
        latitude_deg=lat_d,
        latitude_min=lat_m,
        latitude_ns=lat_ns if lat_d is not None else None,
        longitude_deg=lon_d,
        longitude_min=lon_m,
        longitude_ew=lon_ew if lon_d is not None else None,
        distance_nm=dist,
        created_by=user.full_name,
    )
    db.add(evt)
    await db.flush()

    params = await get_mrv_params(db)
    await recalculate_all_events(db, leg_id, params)

    await log_activity(db, user, "mrv", "create_from_sof", "MrvEvent", evt.id,
                       f"MRV {mrv_type} depuis SOF #{sof_event_id}")

    return RedirectResponse(url=f"/mrv/leg/{leg_id}", status_code=303)


# ═══════════════════════════════════════════════════════════════
#  EDIT MRV EVENT
# ═══════════════════════════════════════════════════════════════
@router.post("/events/{event_id}/edit", response_class=HTMLResponse)
async def mrv_edit_event(
    event_id: int,
    request: Request,
    timestamp_date: str = Form(...),
    timestamp_time: str = Form("00:00"),
    port_me_do_counter: str = Form(""),
    stbd_me_do_counter: str = Form(""),
    fwd_gen_do_counter: str = Form(""),
    aft_gen_do_counter: str = Form(""),
    rob_mt: str = Form(""),
    cargo_mrv_mt: str = Form(""),
    bunkering_qty_mt: str = Form(""),
    bunkering_date: str = Form(""),
    latitude_deg: str = Form(""),
    latitude_min: str = Form(""),
    latitude_ns: str = Form("N"),
    longitude_deg: str = Form(""),
    longitude_min: str = Form(""),
    longitude_ew: str = Form("E"),
    distance_nm: str = Form(""),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    evt = await db.get(MrvEvent, event_id)
    if not evt:
        raise HTTPException(404)

    try:
        ts = datetime.strptime(f"{timestamp_date} {timestamp_time}", "%Y-%m-%d %H:%M")
        ts = ts.replace(tzinfo=timezone.utc)
    except ValueError:
        raise HTTPException(400, "Format date/heure invalide")

    evt.timestamp_utc = ts
    evt.port_me_do_counter = pf(port_me_do_counter)
    evt.stbd_me_do_counter = pf(stbd_me_do_counter)
    evt.fwd_gen_do_counter = pf(fwd_gen_do_counter)
    evt.aft_gen_do_counter = pf(aft_gen_do_counter)
    evt.rob_mt = pf(rob_mt)
    evt.cargo_mrv_mt = pf(cargo_mrv_mt)
    if evt.event_type == "departure":
        evt.bunkering_qty_mt = pf(bunkering_qty_mt)
        evt.bunkering_date = datetime.strptime(bunkering_date, "%Y-%m-%d").date() if bunkering_date else None
    evt.latitude_deg = pi(latitude_deg)
    evt.latitude_min = pi(latitude_min)
    evt.latitude_ns = latitude_ns if pi(latitude_deg) is not None else None
    evt.longitude_deg = pi(longitude_deg)
    evt.longitude_min = pi(longitude_min)
    evt.longitude_ew = longitude_ew if pi(longitude_deg) is not None else None
    evt.distance_nm = pf(distance_nm)

    await db.flush()

    params = await get_mrv_params(db)
    await recalculate_all_events(db, evt.leg_id, params)

    await log_activity(db, user, "mrv", "update", "MrvEvent", event_id, "Modification MRV event")

    return RedirectResponse(url=f"/mrv/leg/{evt.leg_id}", status_code=303)


# ═══════════════════════════════════════════════════════════════
#  DELETE MRV EVENT
# ═══════════════════════════════════════════════════════════════
@router.delete("/events/{event_id}", response_class=HTMLResponse)
async def mrv_delete_event(
    event_id: int,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    evt = await db.get(MrvEvent, event_id)
    if not evt:
        raise HTTPException(404)
    leg_id = evt.leg_id
    await db.delete(evt)
    await db.flush()

    # Recalculate remaining events
    params = await get_mrv_params(db)
    await recalculate_all_events(db, leg_id, params)

    await log_activity(db, user, "mrv", "delete", "MrvEvent", event_id, "Suppression MRV event")
    return HTMLResponse(content="", status_code=200)


# ═══════════════════════════════════════════════════════════════
#  MRV PARAMETERS (Admin)
# ═══════════════════════════════════════════════════════════════
@router.post("/params/save", response_class=HTMLResponse)
async def mrv_save_params(
    request: Request,
    avg_mdo_density: str = Form("0.845"),
    mdo_admissible_deviation: str = Form("2.0"),
    co2_emission_factor: str = Form("3.206"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.permissions import can_delete
    if not can_delete(user, "mrv"):
        raise HTTPException(403, "Droits administrateur requis")

    updates = {
        "avg_mdo_density": pf(avg_mdo_density) or 0.845,
        "mdo_admissible_deviation": pf(mdo_admissible_deviation) or 2.0,
        "co2_emission_factor": pf(co2_emission_factor) or 3.206,
    }

    for name, value in updates.items():
        result = await db.execute(select(MrvParameter).where(MrvParameter.parameter_name == name))
        param = result.scalar_one_or_none()
        if param:
            param.parameter_value = value
        else:
            info = MRV_DEFAULTS.get(name, {})
            db.add(MrvParameter(
                parameter_name=name,
                parameter_value=value,
                unit=info.get("unit", ""),
                description=info.get("description", ""),
            ))

    await db.flush()
    await log_activity(db, user, "mrv", "update_params", "MrvParameter", None, "MRV params updated")

    return RedirectResponse(url="/mrv", status_code=303)


# ═══════════════════════════════════════════════════════════════
#  DNV VERACITY CSV EXPORT (18 columns exact format)
# ═══════════════════════════════════════════════════════════════
@router.get("/export/dnv-csv", response_class=StreamingResponse)
async def export_dnv_csv(
    request: Request,
    vessel: Optional[int] = Query(None),
    year: Optional[int] = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export MRV data in DNV Veracity compatible CSV format (18 columns)."""
    current_year = year or datetime.now().year

    query = (
        select(MrvEvent)
        .join(Leg, MrvEvent.leg_id == Leg.id)
        .options(selectinload(MrvEvent.leg).selectinload(Leg.vessel))
        .options(selectinload(MrvEvent.leg).selectinload(Leg.departure_port))
        .options(selectinload(MrvEvent.leg).selectinload(Leg.arrival_port))
        .where(Leg.year == current_year)
    )

    if vessel:
        v_result = await db.execute(select(Vessel).where(Vessel.code == vessel))
        v = v_result.scalar_one_or_none()
        if v:
            query = query.where(Leg.vessel_id == v.id)

    query = query.order_by(MrvEvent.timestamp_utc.asc())
    result = await db.execute(query)
    events = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output, delimiter=",")

    # Header row (18 columns as specified in MRV requirements)
    writer.writerow([
        "IMO", "Date_UTC", "Time_UTC", "Voyage_From", "Voyage_To",
        "Event", "Time_Since_Previous_Report", "Distance", "Cargo_Mt",
        "ME_Consumption_MDO", "AE_Consumption_MDO", "MDO_ROB",
        "Latitude_Degree", "Latitude_Minutes", "Latitude_North_South",
        "Longitude_Degree", "Longitude_Minutes", "Longitude_East_West",
    ])

    prev_ts = None
    for evt in events:
        leg = evt.leg
        vessel_obj = leg.vessel if leg else None

        # Time since previous report (hours)
        hours_since = 0
        if prev_ts and evt.timestamp_utc:
            delta = evt.timestamp_utc - prev_ts
            hours_since = int(delta.total_seconds() / 3600)

        # Event label for DNV
        event_labels = {
            "departure": "Departure",
            "arrival": "Arrival",
            "at_sea": "At Sea",
            "begin_anchoring": "Begin Anchoring/Drifting",
            "end_anchoring": "End Anchoring/Drifting",
        }

        writer.writerow([
            vessel_obj.imo_number if vessel_obj else "",
            evt.timestamp_utc.strftime("%Y-%m-%d") if evt.timestamp_utc else "",
            evt.timestamp_utc.strftime("%H:%M") if evt.timestamp_utc else "",
            leg.departure_port_locode if leg else "",
            leg.arrival_port_locode if leg else "",
            event_labels.get(evt.event_type, evt.event_type),
            hours_since,
            int(evt.distance_nm or 0),
            round(evt.cargo_mrv_mt, 1) if evt.cargo_mrv_mt else "",
            round(evt.me_consumption_mdo, 4) if evt.me_consumption_mdo else "",
            round(evt.ae_consumption_mdo, 4) if evt.ae_consumption_mdo else "",
            round(evt.rob_mt, 1) if evt.rob_mt else "",
            evt.latitude_deg if evt.latitude_deg is not None else "",
            evt.latitude_min if evt.latitude_min is not None else "",
            evt.latitude_ns or "",
            evt.longitude_deg if evt.longitude_deg is not None else "",
            evt.longitude_min if evt.longitude_min is not None else "",
            evt.longitude_ew or "",
        ])

        if evt.timestamp_utc:
            prev_ts = evt.timestamp_utc

    output.seek(0)

    vessel_name = ""
    if vessel:
        v_r = await db.execute(select(Vessel).where(Vessel.code == vessel))
        v_o = v_r.scalar_one_or_none()
        vessel_name = f"_{v_o.name}" if v_o else ""

    fname = f"MRV_DNV{vessel_name}_{current_year}_{date.today().strftime('%Y%m%d')}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={fname}"},
    )


# ═══════════════════════════════════════════════════════════════
#  CARBON REPORT PDF
# ═══════════════════════════════════════════════════════════════
@router.get("/export/carbon-report", response_class=StreamingResponse)
async def export_carbon_report(
    request: Request,
    vessel: Optional[int] = Query(None),
    year: Optional[int] = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate Carbon Report PDF. Blocked if quality errors exist."""
    from io import BytesIO
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

    current_year = year or datetime.now().year

    query = (
        select(MrvEvent)
        .join(Leg, MrvEvent.leg_id == Leg.id)
        .options(selectinload(MrvEvent.leg).selectinload(Leg.vessel))
        .options(selectinload(MrvEvent.leg).selectinload(Leg.departure_port))
        .options(selectinload(MrvEvent.leg).selectinload(Leg.arrival_port))
        .where(Leg.year == current_year)
    )

    vessel_obj = None
    if vessel:
        v_result = await db.execute(select(Vessel).where(Vessel.code == vessel))
        vessel_obj = v_result.scalar_one_or_none()
        if vessel_obj:
            query = query.where(Leg.vessel_id == vessel_obj.id)

    query = query.order_by(MrvEvent.timestamp_utc.asc())
    result = await db.execute(query)
    events = result.scalars().all()

    # Check for quality errors - block report if present
    error_events = [e for e in events if e.quality_status == "error"]
    if error_events:
        raise HTTPException(
            400,
            f"Carbon Report bloqué : {len(error_events)} événement(s) avec erreurs qualité. "
            "Corrigez les données avant de générer le rapport."
        )

    params = await get_mrv_params(db)
    co2_factor = params.get("co2_emission_factor", 3.206)

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4),
                            topMargin=15*mm, bottomMargin=12*mm,
                            leftMargin=10*mm, rightMargin=10*mm)
    styles = getSampleStyleSheet()
    elements = []

    hdr_color = colors.HexColor("#095561")
    title_style = ParagraphStyle("CRTitle", parent=styles["Heading1"],
                                  fontSize=16, textColor=hdr_color, spaceAfter=4)
    sub_style = ParagraphStyle("Sub", parent=styles["Normal"],
                                fontSize=10, textColor=colors.HexColor("#555"), spaceAfter=2)

    elements.append(Paragraph("CARBON REPORT — MRV", title_style))
    vessel_name = vessel_obj.name if vessel_obj else "All Vessels"
    imo = vessel_obj.imo_number if vessel_obj else ""
    elements.append(Paragraph(
        f"<b>Vessel:</b> {vessel_name} &nbsp; <b>IMO:</b> {imo} &nbsp; <b>Year:</b> {current_year}",
        sub_style
    ))
    elements.append(Spacer(1, 6*mm))

    # Summary
    total_consumption = sum(e.total_consumption_mdo or 0 for e in events)
    total_co2 = total_consumption * co2_factor
    total_me = sum(e.me_consumption_mdo or 0 for e in events)
    total_ae = sum(e.ae_consumption_mdo or 0 for e in events)

    summary_data = [
        ["Total ME Consumption (mt)", f"{total_me:.2f}"],
        ["Total AE Consumption (mt)", f"{total_ae:.2f}"],
        ["Total MDO Consumption (mt)", f"{total_consumption:.2f}"],
        [f"Total CO\u2082 Emissions (mt)", f"{total_co2:.2f}"],
        ["CO\u2082 Emission Factor", f"{co2_factor} t CO\u2082/t fuel"],
        ["MDO Density", f"{params.get('avg_mdo_density', 0.845)} t/m\u00b3"],
    ]
    st = Table(summary_data, colWidths=[200, 150])
    st.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#ddd")),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f0f7f8")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(st)
    elements.append(Spacer(1, 6*mm))

    # Events table
    elements.append(Paragraph("Event Details", ParagraphStyle("S2", parent=styles["Heading2"],
                                                               fontSize=12, textColor=hdr_color)))
    elements.append(Spacer(1, 3*mm))

    data = [["Date UTC", "Time", "Event", "Voyage", "Cargo (mt)",
             "ME (mt)", "AE (mt)", "Total (mt)", "ROB (mt)", "CO\u2082 (mt)", "Quality"]]

    for evt in events:
        leg = evt.leg
        route = f"{leg.departure_port_locode}→{leg.arrival_port_locode}" if leg else ""
        evt_co2 = (evt.total_consumption_mdo or 0) * co2_factor

        event_labels = {
            "departure": "DEP", "arrival": "ARR", "at_sea": "SEA",
            "begin_anchoring": "B.ANC", "end_anchoring": "E.ANC",
        }
        quality_labels = {"ok": "OK", "warning": "WARN", "error": "ERR", "pending": "..."}

        data.append([
            evt.timestamp_utc.strftime("%Y-%m-%d") if evt.timestamp_utc else "",
            evt.timestamp_utc.strftime("%H:%M") if evt.timestamp_utc else "",
            event_labels.get(evt.event_type, evt.event_type),
            route,
            f"{evt.cargo_mrv_mt:.1f}" if evt.cargo_mrv_mt else "",
            f"{evt.me_consumption_mdo:.3f}" if evt.me_consumption_mdo else "",
            f"{evt.ae_consumption_mdo:.3f}" if evt.ae_consumption_mdo else "",
            f"{evt.total_consumption_mdo:.3f}" if evt.total_consumption_mdo else "",
            f"{evt.rob_mt:.1f}" if evt.rob_mt else "",
            f"{evt_co2:.3f}" if evt_co2 else "",
            quality_labels.get(evt.quality_status, "?"),
        ])

    col_widths = [65, 40, 40, 70, 55, 55, 55, 55, 55, 55, 40]
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), hdr_color),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 7),
        ("FONTSIZE", (0, 1), (-1, -1), 7),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#ddd")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9fafb")]),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    elements.append(t)

    # Footer
    elements.append(Spacer(1, 8*mm))
    footer_style = ParagraphStyle("Footer", parent=styles["Normal"],
                                   fontSize=8, textColor=colors.HexColor("#aaa"))
    elements.append(Paragraph(
        f"Generated {date.today().strftime('%d/%m/%Y')} — TOWT Operations Platform — MRV Carbon Report",
        footer_style
    ))

    doc.build(elements)
    buf.seek(0)

    vessel_suffix = f"_{vessel_obj.name}" if vessel_obj else ""
    fname = f"Carbon_Report{vessel_suffix}_{current_year}_{date.today().strftime('%Y%m%d')}.pdf"
    return StreamingResponse(
        buf, media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={fname}"},
    )


# ═══════════════════════════════════════════════════════════════
#  RECALCULATE ALL (manual trigger)
# ═══════════════════════════════════════════════════════════════
@router.post("/leg/{leg_id}/recalculate", response_class=HTMLResponse)
async def mrv_recalculate(
    leg_id: int,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    params = await get_mrv_params(db)
    await recalculate_all_events(db, leg_id, params)
    await log_activity(db, user, "mrv", "recalculate", "MrvEvent", leg_id, "Recalcul MRV")
    return RedirectResponse(url=f"/mrv/leg/{leg_id}", status_code=303)
