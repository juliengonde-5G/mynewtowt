from fastapi import APIRouter, Request, Depends, Form, HTTPException, Query, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from app.templating import templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import Optional
from datetime import datetime, timedelta, timezone, date
import os
import uuid

from app.database import get_db
from app.auth import get_current_user
from app.permissions import require_permission
from app.models.user import User
from app.models.vessel import Vessel
from app.models.leg import Leg
from app.utils.timezones import get_port_timezone, utc_offset_label, TIMEZONE_CHOICES
from app.models.operation import EscaleOperation, DockerShift
from app.models.crew import CrewMember, CrewAssignment, CrewTicket, TRANSPORT_MODES
from app.models.finance import LegFinance, OpexParameter
from app.models.order import Order, OrderAssignment
from app.utils.activity import log_activity
from app.utils.notifications import notify_arrival, notify_departure

TICKET_UPLOAD_DIR = "/app/uploads/crew_tickets"

router = APIRouter(prefix="/escale", tags=["escale"])

OPERATION_TYPES = [
    {"value": "relations_externes", "label": "Relations Externes", "icon": "\U0001f4e2", "color": "#16a34a"},
    {"value": "technique", "label": "Technique", "icon": "\U0001f527", "color": "#F59E0B"},
    {"value": "armement", "label": "Armement", "icon": "\U0001f6e1", "color": "#60A5FA"},
]

ACTIONS_BY_TYPE = {
    "relations_externes": [
        {"value": "relation_presse", "label": "Relation Presse"},
        {"value": "relation_client", "label": "Relation Client"},
        {"value": "relation_prospect", "label": "Relation Prospect"},
    ],
    "technique": [
        {"value": "soutage", "label": "Soutage"},
        {"value": "intervention_technique", "label": "Intervention technique"},
        {"value": "inspection_technique", "label": "Inspection technique"},
    ],
    "armement": [
        {"value": "embarquement", "label": "Embarquement"},
        {"value": "debarquement", "label": "D\u00e9barquement"},
        {"value": "medicale", "label": "Visite m\u00e9dicale"},
        {"value": "avitaillement", "label": "Avitaillement"},
        {"value": "inspection_armement", "label": "Inspection armement"},
        {"value": "passage_paf", "label": "Passage Police Aux Frontières"},
    ],
}

CREW_ACTIONS = {"embarquement", "debarquement"}

FECAMP_LOCODES = {"FRFEC"}  # Fécamp port LOCODE(s)


def compute_ticket_alerts(tickets, leg):
    """Check ticket dates against escale dates. Returns list of alert dicts."""
    alerts = []
    if not leg or not tickets:
        return alerts
    # Escale window: ATA (or ETA) to ATD (or ETD of next leg estimate)
    escale_start = (leg.ata or leg.eta)
    escale_end = leg.atd
    if not escale_end and escale_start:
        escale_end = escale_start + timedelta(days=leg.port_stay_days or 3)

    for t in tickets:
        if not t.ticket_date:
            continue
        # Convert escale dates to date for comparison
        esc_start_date = escale_start.date() if escale_start else None
        esc_end_date = escale_end.date() if escale_end else None

        incompatible = False
        reason = ""
        if esc_start_date and t.ticket_date < esc_start_date - timedelta(days=1):
            incompatible = True
            reason = f"Billet le {t.ticket_date.strftime('%d/%m')} avant l'escale ({esc_start_date.strftime('%d/%m')})"
        elif esc_end_date and t.ticket_date > esc_end_date + timedelta(days=1):
            incompatible = True
            reason = f"Billet le {t.ticket_date.strftime('%d/%m')} après l'escale ({esc_end_date.strftime('%d/%m')})"

        if incompatible:
            alerts.append({
                "ticket": t,
                "member_name": t.member.full_name if t.member else "?",
                "reason": reason,
            })
    return alerts

PORT_STATUSES = [
    {"value": "pilote_arrivee", "label": "Pilote \u00e0 bord \u2014 Arriv\u00e9e", "icon": "\U0001f6a2", "vessel_status": "en_mer"},
    {"value": "a_quai", "label": "\u00c0 quai", "icon": "\u2693", "vessel_status": "a_quai"},
    {"value": "pilote_depart", "label": "Pilote \u00e0 bord \u2014 D\u00e9part", "icon": "\u26f5", "vessel_status": "en_mer"},
]

ACTION_LABELS = {}
for cat_actions in ACTIONS_BY_TYPE.values():
    for a in cat_actions:
        ACTION_LABELS[a["value"]] = a["label"]


def parse_float(val, default=None):
    if val is None or (isinstance(val, str) and val.strip() == ""):
        return default
    try:
        return float(val)
    except Exception:
        return default


def parse_int(val, default=None):
    if val is None or (isinstance(val, str) and val.strip() == ""):
        return default
    try:
        return int(val)
    except Exception:
        return default


def parse_datetime(val):
    if val is None or (isinstance(val, str) and val.strip() == ""):
        return None
    try:
        return datetime.fromisoformat(val)
    except Exception:
        return None


def get_quay_bounds(leg):
    quay_start = leg.ata or leg.eta
    quay_end = leg.atd
    if not quay_end and quay_start:
        quay_end = quay_start + timedelta(days=leg.port_stay_days or 3)
    return quay_start, quay_end


def compute_port_status(leg):
    if leg.atd:
        return "pilote_depart"
    elif leg.ata:
        return "a_quai"
    else:
        return "pilote_arrivee"


def is_leg_terminated(leg):
    return bool(leg.atd)


def is_leg_locked(leg):
    return leg.status == "completed"


async def update_finance_actual_duration(db: AsyncSession, leg: Leg):
    """Recalculate finance OPEX actual based on real navigation duration.

    When ATA is set, we can compute the actual sea days:
    - If both ETD and ATA available: actual_hours = ATA - ETD
    - Recalculate sea_cost_actual = opex_daily × actual_sea_days
    """
    if not leg.ata:
        return
    # Get departure time: ATD of previous leg, or ETD of this leg
    departure_time = leg.etd
    if departure_time and leg.ata:
        actual_hours = (leg.ata - departure_time).total_seconds() / 3600
        actual_sea_days = actual_hours / 24 if actual_hours > 0 else 0
    else:
        actual_sea_days = 0

    # Estimated sea_days for comparison
    estimated_hours = leg.estimated_duration_hours or 0
    estimated_sea_days = estimated_hours / 24

    # Get OPEX daily rate
    opex_result = await db.execute(
        select(OpexParameter).where(OpexParameter.parameter_name == "opex_daily_rate")
    )
    opex_param = opex_result.scalar_one_or_none()
    opex_daily = opex_param.parameter_value if opex_param else 11600

    # Get or create LegFinance
    fin_result = await db.execute(select(LegFinance).where(LegFinance.leg_id == leg.id))
    fin = fin_result.scalar_one_or_none()
    if not fin:
        fin = LegFinance(leg_id=leg.id)
        db.add(fin)

    # Update actual OPEX based on real navigation duration
    fin.sea_cost_actual = round(opex_daily * actual_sea_days, 0)
    # Ensure forecast is also computed if empty
    if not fin.sea_cost_forecast:
        fin.sea_cost_forecast = round(opex_daily * estimated_sea_days, 0)
    fin.compute()
    await db.flush()


async def propagate_from_leg(db: AsyncSession, leg: Leg):
    result = await db.execute(
        select(Leg).options(selectinload(Leg.vessel), selectinload(Leg.departure_port), selectinload(Leg.arrival_port))
        .where(Leg.vessel_id == leg.vessel_id, Leg.year == leg.year, Leg.sequence > leg.sequence)
        .order_by(Leg.sequence)
    )
    subsequent = result.scalars().all()
    prev_eta = leg.ata or leg.eta
    for nleg in subsequent:
        if prev_eta and not nleg.atd:
            nleg.etd = prev_eta + timedelta(days=nleg.port_stay_days or 3)
        if nleg.etd and nleg.distance_nm:
            speed = nleg.speed_knots or 8.0
            elong = nleg.elongation_coeff or 1.25
            hours = (nleg.distance_nm * elong) / speed
            nleg.eta = nleg.etd + timedelta(hours=hours)
            nleg.computed_distance = round(nleg.distance_nm * elong, 1)
            nleg.estimated_duration_hours = round(hours, 1)
        prev_eta = nleg.ata or nleg.eta
    await db.flush()


async def handle_crew_assignment(db: AsyncSession, op: EscaleOperation, crew_ids: list):
    if not crew_ids or op.action not in CREW_ACTIONS:
        return
    leg_result = await db.execute(select(Leg).options(selectinload(Leg.vessel)).where(Leg.id == op.leg_id))
    leg = leg_result.scalar_one_or_none()
    if not leg:
        return
    op_date = (op.actual_start or op.planned_start or datetime.now(timezone.utc)).date()
    for cid in crew_ids:
        if op.action == "embarquement":
            db.add(CrewAssignment(
                member_id=cid, vessel_id=leg.vessel_id,
                embark_date=op_date, embark_leg_id=leg.id, status="active",
            ))
        elif op.action == "debarquement":
            result = await db.execute(
                select(CrewAssignment).where(
                    CrewAssignment.member_id == cid,
                    CrewAssignment.vessel_id == leg.vessel_id,
                    CrewAssignment.status == "active",
                ).order_by(CrewAssignment.embark_date.desc()).limit(1)
            )
            assignment = result.scalar_one_or_none()
            if assignment:
                assignment.disembark_date = op_date
                assignment.disembark_leg_id = leg.id
                assignment.status = "completed"
    await db.flush()


# === ESCALE HOME ===
@router.get("", response_class=HTMLResponse)
async def escale_home(
    request: Request,
    vessel: Optional[int] = Query(None),
    year: Optional[int] = Query(None),
    leg_id: Optional[int] = Query(None),
    user: User = Depends(require_permission("escale", "C")),
    db: AsyncSession = Depends(get_db),
):
    current_year = year or datetime.now().year
    years = list(range(2025, datetime.now().year + 2))
    vessels_result = await db.execute(select(Vessel).where(Vessel.is_active == True).order_by(Vessel.code))
    vessels = vessels_result.scalars().all()
    selected_vessel = vessel or (vessels[0].code if vessels else None)

    vessel_obj = None
    if selected_vessel:
        v_result = await db.execute(select(Vessel).where(Vessel.code == selected_vessel))
        vessel_obj = v_result.scalar_one_or_none()

    legs = []
    if vessel_obj:
        legs_result = await db.execute(
            select(Leg).options(selectinload(Leg.departure_port), selectinload(Leg.arrival_port))
            .where(Leg.vessel_id == vessel_obj.id, Leg.year == current_year)
            .order_by(Leg.sequence)
        )
        legs = legs_result.scalars().all()

    selected_leg = None
    next_leg = None
    operations = []
    docker_shifts = []
    vessel_status = "en_mer"
    port_status = "pilote_arrivee"
    quay_start_str = ""
    quay_end_str = ""
    leg_terminated = False
    leg_locked = False

    if leg_id:
        leg_result = await db.execute(
            select(Leg).options(
                selectinload(Leg.vessel),
                selectinload(Leg.departure_port),
                selectinload(Leg.arrival_port),
            ).where(Leg.id == leg_id)
        )
        selected_leg = leg_result.scalar_one_or_none()
        if selected_leg:
            ops_result = await db.execute(
                select(EscaleOperation).where(EscaleOperation.leg_id == leg_id)
                .order_by(EscaleOperation.planned_start.asc().nulls_last(), EscaleOperation.id)
            )
            operations = ops_result.scalars().all()
            ds_result = await db.execute(
                select(DockerShift).where(DockerShift.leg_id == leg_id)
                .order_by(DockerShift.planned_start.asc().nulls_last())
            )
            docker_shifts = ds_result.scalars().all()

            # Query next leg (departing from this leg's arrival port)
            if vessel_obj:
                next_result = await db.execute(
                    select(Leg).options(
                        selectinload(Leg.departure_port),
                        selectinload(Leg.arrival_port),
                    )
                    .where(
                        Leg.vessel_id == vessel_obj.id,
                        Leg.sequence > selected_leg.sequence,
                    )
                    .order_by(Leg.sequence)
                    .limit(1)
                )
                next_leg = next_result.scalar_one_or_none()

            # ── Determine vessel status ──
            # Compare current time with leg dates (must be tz-aware for comparison)
            now_utc = datetime.now(timezone.utc)
            departure_time = selected_leg.atd or selected_leg.etd

            if selected_leg.ata:
                # Vessel has arrived at destination → at berth
                vessel_status = "a_quai"
                port_status = compute_port_status(selected_leg)
            elif selected_leg.atd or (departure_time and now_utc >= departure_time):
                # Vessel has departed (or past ETD) → at sea
                vessel_status = "en_mer"
                port_status = "pilote_arrivee"
            else:
                # Vessel hasn't departed yet → still at departure port
                vessel_status = "a_quai"
                port_status = "pilote_arrivee"

            qs, qe = get_quay_bounds(selected_leg)
            if qs:
                quay_start_str = qs.strftime('%Y-%m-%dT%H:%M')
            if qe:
                quay_end_str = qe.strftime('%Y-%m-%dT%H:%M')
            leg_terminated = is_leg_terminated(selected_leg)
            leg_locked = is_leg_locked(selected_leg)

    # Compute performance metrics when ATA is available
    perf = None
    if selected_leg and selected_leg.ata and selected_leg.etd:
        # Actual duration: ATD → ATA (fallback to ETD if no ATD)
        departure_actual = selected_leg.atd or selected_leg.etd
        actual_hours = (selected_leg.ata - departure_actual).total_seconds() / 3600
        # Estimated duration: from model, or ETD → ETA
        estimated_hours = selected_leg.estimated_duration_hours or 0
        if not estimated_hours and selected_leg.eta:
            estimated_hours = (selected_leg.eta - selected_leg.etd).total_seconds() / 3600
        delta_hours = actual_hours - estimated_hours if estimated_hours else 0
        perf = {
            "actual_hours": round(actual_hours, 1),
            "actual_days": round(actual_hours / 24, 1),
            "estimated_hours": round(estimated_hours, 1),
            "estimated_days": round(estimated_hours / 24, 1),
            "delta_hours": round(delta_hours, 1),
            "delta_days": round(delta_hours / 24, 1),
            "delta_pct": round((delta_hours / estimated_hours * 100), 1) if estimated_hours else 0,
        }
        # Load finance for OPEX comparison
        fin_result = await db.execute(select(LegFinance).where(LegFinance.leg_id == selected_leg.id))
        fin = fin_result.scalar_one_or_none()
        if fin:
            perf["opex_forecast"] = fin.sea_cost_forecast or 0
            perf["opex_actual"] = fin.sea_cost_actual or 0
            perf["opex_delta"] = round((fin.sea_cost_actual or 0) - (fin.sea_cost_forecast or 0), 0)

    # Load crew tickets for this leg
    crew_tickets = []
    ticket_alerts = []
    if selected_leg:
        tickets_result = await db.execute(
            select(CrewTicket).options(selectinload(CrewTicket.member))
            .where(CrewTicket.leg_id == selected_leg.id)
            .order_by(CrewTicket.ticket_date.asc())
        )
        crew_tickets = tickets_result.scalars().all()
        ticket_alerts = compute_ticket_alerts(crew_tickets, selected_leg)

    # Load active crew for ticket form dropdown
    crew_for_tickets = []
    if selected_leg:
        crew_result = await db.execute(
            select(CrewMember).where(CrewMember.is_active == True)
            .order_by(CrewMember.role, CrewMember.last_name)
        )
        crew_for_tickets = crew_result.scalars().all()

    # ── Commercial visibility: orders assigned to this leg ──
    leg_orders = []
    leg_orders_summary = {"count": 0, "palettes": 0, "weight": 0, "revenue": 0}
    if selected_leg:
        oa_result = await db.execute(
            select(OrderAssignment)
            .options(selectinload(OrderAssignment.order))
            .where(OrderAssignment.leg_id == selected_leg.id)
        )
        assignments = oa_result.scalars().all()
        for a in assignments:
            if a.order:
                leg_orders.append(a.order)
                leg_orders_summary["count"] += 1
                leg_orders_summary["palettes"] += a.order.quantity_palettes or 0
                leg_orders_summary["weight"] += a.order.total_weight or 0
                leg_orders_summary["revenue"] += float(a.order.total_price or 0)
        leg_orders_summary["weight"] = round(leg_orders_summary["weight"], 1)
        leg_orders_summary["revenue"] = round(leg_orders_summary["revenue"], 2)

    return templates.TemplateResponse("escale/index.html", {
        "request": request, "user": user,
        "vessels": vessels, "selected_vessel": selected_vessel, "vessel_obj": vessel_obj,
        "current_year": current_year, "years": years,
        "legs": legs, "selected_leg": selected_leg, "next_leg": next_leg, "leg_id": leg_id,
        "operations": operations, "docker_shifts": docker_shifts,
        "vessel_status": vessel_status, "port_status": port_status,
        "port_statuses": PORT_STATUSES,
        "quay_start": quay_start_str, "quay_end": quay_end_str,
        "leg_terminated": leg_terminated, "leg_locked": leg_locked,
        "operation_types": OPERATION_TYPES, "actions_by_type": ACTIONS_BY_TYPE,
        "perf": perf,
        "crew_tickets": crew_tickets, "ticket_alerts": ticket_alerts,
        "crew_for_tickets": crew_for_tickets, "transport_modes": TRANSPORT_MODES,
        "tz_choices": TIMEZONE_CHOICES,
        "port_timezone": get_port_timezone(selected_leg.departure_port.country_code, selected_leg.departure_port.zone_code) if selected_leg and selected_leg.departure_port else "UTC",
        "port_tz_label": selected_leg.departure_port.name if selected_leg and selected_leg.departure_port else "Port",
        "port_tz_offset": utc_offset_label(get_port_timezone(selected_leg.departure_port.country_code, selected_leg.departure_port.zone_code)) if selected_leg and selected_leg.departure_port else "UTC",
        "leg_orders": leg_orders,
        "leg_orders_summary": leg_orders_summary,
        "active_module": "escale",
    })


# === PORT STATUS (button progression) ===
@router.post("/legs/{lid}/port-status", response_class=HTMLResponse)
async def update_port_status(
    lid: int, request: Request,
    new_status: str = Form(...),
    status_time: Optional[str] = Form(None),
    user: User = Depends(require_permission("escale", "M")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Leg).options(selectinload(Leg.vessel), selectinload(Leg.departure_port), selectinload(Leg.arrival_port))
        .where(Leg.id == lid)
    )
    leg = result.scalar_one_or_none()
    if not leg:
        raise HTTPException(404)

    now = parse_datetime(status_time) or datetime.now(timezone.utc)
    vessel_name = leg.vessel.name if leg.vessel else "Navire"
    port_name = leg.arrival_port.name if leg.arrival_port else leg.arrival_port_locode

    if new_status == "a_quai":
        leg.ata = now
        leg.status = "in_progress"
        await propagate_from_leg(db, leg)
        # Recalculate finance with actual navigation duration
        await update_finance_actual_duration(db, leg)
        # Notify company: arrival at dock
        await notify_arrival(db, leg, vessel_name, port_name)

    elif new_status == "pilote_depart":
        # F37: do NOT auto-fabricate an ATA — require operator to have set it
        # via the 'a_quai' transition. Forcing departure without arrival leaves
        # ATA null so the legitimate operator sees the missing field.
        if not leg.ata:
            raise HTTPException(
                400,
                "Impossible de passer en 'pilote départ' sans ATA renseignée. "
                "Passer d'abord au statut 'à quai'."
            )
        leg.atd = now
        leg.status = "completed"
        await propagate_from_leg(db, leg)
        # Recalculate finance with final actual data
        await update_finance_actual_duration(db, leg)
        # Notify company: departure
        dep_port_name = leg.arrival_port.name if leg.arrival_port else leg.arrival_port_locode
        await notify_departure(db, leg, vessel_name, dep_port_name)

    await db.flush()
    await log_activity(db, user, "escale", "port_status", "Leg", lid, f"Statut port → {new_status}")
    url = f"/escale?vessel={leg.vessel.code}&year={leg.year}&leg_id={lid}"
    if request.headers.get("HX-Request"):
        return HTMLResponse(content="", headers={"HX-Redirect": url})
    return RedirectResponse(url=url, status_code=303)


# === LOCK / UNLOCK ===
@router.post("/legs/{lid}/lock", response_class=HTMLResponse)
async def lock_leg(lid: int, request: Request, user: User = Depends(require_permission("escale", "M")), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Leg).options(selectinload(Leg.vessel)).where(Leg.id == lid))
    leg = result.scalar_one_or_none()
    if not leg:
        raise HTTPException(404)
    leg.status = "completed"
    await db.flush()
    await log_activity(db, user, "escale", "lock", "Leg", lid, "Verrouillage escale")
    url = f"/escale?vessel={leg.vessel.code}&year={leg.year}&leg_id={lid}"
    if request.headers.get("HX-Request"):
        return HTMLResponse(content="", headers={"HX-Redirect": url})
    return RedirectResponse(url=url, status_code=303)


@router.post("/legs/{lid}/unlock", response_class=HTMLResponse)
async def unlock_leg(lid: int, request: Request, user: User = Depends(require_permission("escale", "M")), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Leg).options(selectinload(Leg.vessel)).where(Leg.id == lid))
    leg = result.scalar_one_or_none()
    if not leg:
        raise HTTPException(404)
    leg.status = "planned"
    await db.flush()
    await log_activity(db, user, "escale", "unlock", "Leg", lid, "Déverrouillage escale")
    url = f"/escale?vessel={leg.vessel.code}&year={leg.year}&leg_id={lid}"
    if request.headers.get("HX-Request"):
        return HTMLResponse(content="", headers={"HX-Redirect": url})
    return RedirectResponse(url=url, status_code=303)


# === PDF EXPORT ===
@router.get("/legs/{lid}/pdf", response_class=HTMLResponse)
async def escale_pdf(lid: int, request: Request, user: User = Depends(require_permission("escale", "C")), db: AsyncSession = Depends(get_db)):
    leg_result = await db.execute(
        select(Leg).options(selectinload(Leg.vessel), selectinload(Leg.departure_port), selectinload(Leg.arrival_port))
        .where(Leg.id == lid)
    )
    leg = leg_result.scalar_one_or_none()
    if not leg:
        raise HTTPException(404)
    ops_result = await db.execute(
        select(EscaleOperation).where(EscaleOperation.leg_id == lid)
        .order_by(EscaleOperation.planned_start.asc().nulls_last())
    )
    operations = ops_result.scalars().all()
    ds_result = await db.execute(
        select(DockerShift).where(DockerShift.leg_id == lid)
        .order_by(DockerShift.planned_start.asc().nulls_last())
    )
    docker_shifts = ds_result.scalars().all()
    return templates.TemplateResponse("escale/pdf_export.html", {
        "request": request, "leg": leg, "operations": operations, "docker_shifts": docker_shifts,
        "action_labels": ACTION_LABELS, "now": datetime.now(timezone.utc),
    })


# === CREATE OPERATION ===
@router.get("/operations/create", response_class=HTMLResponse)
async def operation_create_form(
    request: Request, leg_id: int = Query(...),
    cat: Optional[str] = Query(None),
    user: User = Depends(require_permission("escale", "M")), db: AsyncSession = Depends(get_db),
):
    leg_result = await db.execute(select(Leg).where(Leg.id == leg_id))
    leg = leg_result.scalar_one_or_none()
    if leg and is_leg_locked(leg):
        raise HTTPException(403, detail="Escale verrouill\u00e9e")
    quay_start_str = ""
    quay_end_str = ""
    if leg:
        qs, qe = get_quay_bounds(leg)
        if qs:
            quay_start_str = qs.strftime('%Y-%m-%dT%H:%M')
        if qe:
            quay_end_str = qe.strftime('%Y-%m-%dT%H:%M')
    crew_result = await db.execute(
        select(CrewMember).where(CrewMember.is_active == True).order_by(CrewMember.role, CrewMember.last_name)
    )
    crew_members = crew_result.scalars().all()
    return templates.TemplateResponse("escale/operation_form.html", {
        "request": request, "user": user,
        "edit_op": None, "leg_id": leg_id,
        "operation_types": OPERATION_TYPES, "actions_by_type": ACTIONS_BY_TYPE,
        "quay_start": quay_start_str, "quay_end": quay_end_str, "error": None,
        "preselect_cat": cat,
        "crew_members": crew_members, "selected_crew_ids": set(),
        "tz_choices": TIMEZONE_CHOICES,
    })


@router.post("/operations/create", response_class=HTMLResponse)
async def operation_create_submit(
    request: Request,
    leg_id: str = Form(...), operation_type: str = Form(...), action: str = Form(...),
    planned_start: Optional[str] = Form(None),
    actual_start: Optional[str] = Form(None),
    intervenant: Optional[str] = Form(None), description: Optional[str] = Form(None),
    user: User = Depends(require_permission("escale", "M")), db: AsyncSession = Depends(get_db),
):
    _leg_id = int(leg_id)
    op = EscaleOperation(
        leg_id=_leg_id, operation_type=operation_type, action=action,
        planned_start=parse_datetime(planned_start),
        actual_start=parse_datetime(actual_start),
        intervenant=intervenant.strip() if intervenant else None,
        description=description.strip() if description else None,
    )
    db.add(op)
    await db.flush()
    await log_activity(db, user, "escale", "create", "Operation", op.id, f"Opération {action}")
    form = await request.form()
    # F42: tolerate malformed crew_ids — drop bad tokens instead of 500
    crew_ids = []
    for _cx in form.getlist("crew_ids"):
        if not _cx:
            continue
        try:
            crew_ids.append(int(_cx))
        except (TypeError, ValueError):
            continue
    if crew_ids:
        await handle_crew_assignment(db, op, crew_ids)
    leg_result = await db.execute(select(Leg).options(selectinload(Leg.vessel)).where(Leg.id == _leg_id))
    leg = leg_result.scalar_one_or_none()
    url = f"/escale?vessel={leg.vessel.code}&year={leg.year}&leg_id={_leg_id}" if leg else "/escale"
    if request.headers.get("HX-Request"):
        return HTMLResponse(content="", headers={"HX-Redirect": url})
    return RedirectResponse(url=url, status_code=303)


# === EDIT OPERATION ===
@router.get("/operations/{op_id}/edit", response_class=HTMLResponse)
async def operation_edit_form(
    op_id: int, request: Request,
    user: User = Depends(require_permission("escale", "M")), db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(EscaleOperation).where(EscaleOperation.id == op_id))
    op = result.scalar_one_or_none()
    if not op:
        raise HTTPException(404)
    leg_result = await db.execute(select(Leg).where(Leg.id == op.leg_id))
    leg = leg_result.scalar_one_or_none()
    quay_start_str = ""
    quay_end_str = ""
    if leg:
        qs, qe = get_quay_bounds(leg)
        if qs:
            quay_start_str = qs.strftime('%Y-%m-%dT%H:%M')
        if qe:
            quay_end_str = qe.strftime('%Y-%m-%dT%H:%M')
    crew_result = await db.execute(
        select(CrewMember).where(CrewMember.is_active == True).order_by(CrewMember.role, CrewMember.last_name)
    )
    crew_members = crew_result.scalars().all()
    return templates.TemplateResponse("escale/operation_form.html", {
        "request": request, "user": user,
        "edit_op": op, "leg_id": op.leg_id,
        "operation_types": OPERATION_TYPES, "actions_by_type": ACTIONS_BY_TYPE,
        "quay_start": quay_start_str, "quay_end": quay_end_str, "error": None,
        "preselect_cat": None,
        "crew_members": crew_members, "selected_crew_ids": set(),
        "tz_choices": TIMEZONE_CHOICES,
    })


@router.post("/operations/{op_id}/edit", response_class=HTMLResponse)
async def operation_edit_submit(
    op_id: int, request: Request,
    operation_type: str = Form(...), action: str = Form(...),
    planned_start: Optional[str] = Form(None),
    actual_start: Optional[str] = Form(None),
    intervenant: Optional[str] = Form(None), description: Optional[str] = Form(None),
    user: User = Depends(require_permission("escale", "M")), db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(EscaleOperation).where(EscaleOperation.id == op_id))
    op = result.scalar_one_or_none()
    if not op:
        raise HTTPException(404)
    op.operation_type = operation_type
    op.action = action
    op.planned_start = parse_datetime(planned_start)
    op.actual_start = parse_datetime(actual_start)
    op.intervenant = intervenant.strip() if intervenant else None
    op.description = description.strip() if description else None
    await db.flush()
    await log_activity(db, user, "escale", "update", "Operation", op_id, f"Modification opération {action}")
    form = await request.form()
    # F42: tolerate malformed crew_ids — drop bad tokens instead of 500
    crew_ids = []
    for _cx in form.getlist("crew_ids"):
        if not _cx:
            continue
        try:
            crew_ids.append(int(_cx))
        except (TypeError, ValueError):
            continue
    if crew_ids:
        await handle_crew_assignment(db, op, crew_ids)
    leg_result = await db.execute(select(Leg).options(selectinload(Leg.vessel)).where(Leg.id == op.leg_id))
    leg = leg_result.scalar_one_or_none()
    url = f"/escale?vessel={leg.vessel.code}&year={leg.year}&leg_id={op.leg_id}" if leg else "/escale"
    if request.headers.get("HX-Request"):
        return HTMLResponse(content="", headers={"HX-Redirect": url})
    return RedirectResponse(url=url, status_code=303)


# === DELETE OPERATION ===
@router.delete("/operations/{op_id}", response_class=HTMLResponse)
async def operation_delete(op_id: int, request: Request, user: User = Depends(require_permission("escale", "S")), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(EscaleOperation).where(EscaleOperation.id == op_id))
    op = result.scalar_one_or_none()
    if not op:
        raise HTTPException(404)
    leg_id = op.leg_id
    saved_action = op.action
    await db.delete(op)
    await db.flush()
    await log_activity(db, user, "escale", "delete", "Operation", op_id, "Suppression opération")
    leg_result = await db.execute(select(Leg).options(selectinload(Leg.vessel)).where(Leg.id == leg_id))
    leg = leg_result.scalar_one_or_none()
    url = f"/escale?vessel={leg.vessel.code}&year={leg.year}&leg_id={leg_id}" if leg else "/escale"
    if request.headers.get("HX-Request"):
        return HTMLResponse(content="", headers={"HX-Redirect": url})
    return RedirectResponse(url=url, status_code=303)


# === DOCKER SHIFTS (keep duration/end) ===
@router.get("/dockers/create", response_class=HTMLResponse)
async def docker_create_form(request: Request, leg_id: int = Query(...), user: User = Depends(require_permission("escale", "M")), db: AsyncSession = Depends(get_db)):
    leg_result = await db.execute(select(Leg).where(Leg.id == leg_id))
    leg = leg_result.scalar_one_or_none()
    if leg and is_leg_locked(leg):
        raise HTTPException(403)
    quay_start_str = ""
    quay_end_str = ""
    if leg:
        qs, qe = get_quay_bounds(leg)
        if qs:
            quay_start_str = qs.strftime('%Y-%m-%dT%H:%M')
        if qe:
            quay_end_str = qe.strftime('%Y-%m-%dT%H:%M')
    return templates.TemplateResponse("escale/docker_form.html", {
        "request": request, "user": user, "edit_ds": None, "leg_id": leg_id,
        "quay_start": quay_start_str, "quay_end": quay_end_str, "error": None,
        "tz_choices": TIMEZONE_CHOICES,
    })


@router.post("/dockers/create", response_class=HTMLResponse)
async def docker_create_submit(
    request: Request, leg_id: str = Form(...), hold: str = Form(...),
    planned_start: Optional[str] = Form(None), planned_end: Optional[str] = Form(None),
    planned_palettes: Optional[str] = Form(None), notes: Optional[str] = Form(None),
    user: User = Depends(require_permission("escale", "M")), db: AsyncSession = Depends(get_db),
):
    _leg_id = int(leg_id)
    _ps = parse_datetime(planned_start)
    _pe = parse_datetime(planned_end)
    # F38: reject docker shifts where planned end is at or before planned start
    if _ps and _pe and _pe <= _ps:
        raise HTTPException(400, "La fin prévue du shift doit être après son début.")
    ds = DockerShift(
        leg_id=_leg_id, hold=hold,
        planned_start=_ps,
        planned_end=_pe,
        planned_palettes=parse_int(planned_palettes),
        notes=notes.strip() if notes else None,
    )
    db.add(ds)
    await db.flush()
    await log_activity(db, user, "escale", "create", "DockerShift", ds.id, f"Docker shift cale {hold}")
    leg_result = await db.execute(select(Leg).options(selectinload(Leg.vessel)).where(Leg.id == _leg_id))
    leg = leg_result.scalar_one_or_none()
    url = f"/escale?vessel={leg.vessel.code}&year={leg.year}&leg_id={_leg_id}" if leg else "/escale"
    if request.headers.get("HX-Request"):
        return HTMLResponse(content="", headers={"HX-Redirect": url})
    return RedirectResponse(url=url, status_code=303)


@router.get("/dockers/{ds_id}/edit", response_class=HTMLResponse)
async def docker_edit_form(ds_id: int, request: Request, user: User = Depends(require_permission("escale", "M")), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DockerShift).where(DockerShift.id == ds_id))
    ds = result.scalar_one_or_none()
    if not ds:
        raise HTTPException(404)
    leg_result = await db.execute(select(Leg).where(Leg.id == ds.leg_id))
    leg = leg_result.scalar_one_or_none()
    quay_start_str = ""
    quay_end_str = ""
    if leg:
        qs, qe = get_quay_bounds(leg)
        if qs:
            quay_start_str = qs.strftime('%Y-%m-%dT%H:%M')
        if qe:
            quay_end_str = qe.strftime('%Y-%m-%dT%H:%M')
    return templates.TemplateResponse("escale/docker_form.html", {
        "request": request, "user": user, "edit_ds": ds, "leg_id": ds.leg_id,
        "quay_start": quay_start_str, "quay_end": quay_end_str, "error": None,
        "tz_choices": TIMEZONE_CHOICES,
    })


@router.post("/dockers/{ds_id}/edit", response_class=HTMLResponse)
async def docker_edit_submit(
    ds_id: int, request: Request, hold: str = Form(...),
    planned_start: Optional[str] = Form(None), planned_end: Optional[str] = Form(None),
    actual_start: Optional[str] = Form(None), actual_end: Optional[str] = Form(None),
    planned_palettes: Optional[str] = Form(None), actual_palettes: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    user: User = Depends(require_permission("escale", "M")), db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(DockerShift).where(DockerShift.id == ds_id))
    ds = result.scalar_one_or_none()
    if not ds:
        raise HTTPException(404)
    ds.hold = hold
    _ps = parse_datetime(planned_start)
    _pe = parse_datetime(planned_end)
    _as = parse_datetime(actual_start)
    _ae = parse_datetime(actual_end)
    # F38: reject shifts with end before/equal start (planned & actual)
    if _ps and _pe and _pe <= _ps:
        raise HTTPException(400, "La fin prévue du shift doit être après son début.")
    if _as and _ae and _ae <= _as:
        raise HTTPException(400, "La fin réelle du shift doit être après son début.")
    ds.planned_start = _ps
    ds.planned_end = _pe
    ds.actual_start = _as
    ds.actual_end = _ae
    ds.planned_palettes = parse_int(planned_palettes)
    ds.actual_palettes = parse_int(actual_palettes)
    ds.notes = notes.strip() if notes else None
    await db.flush()
    await log_activity(db, user, "escale", "update", "DockerShift", ds_id, f"Modification docker shift cale {hold}")
    leg_result = await db.execute(select(Leg).options(selectinload(Leg.vessel)).where(Leg.id == ds.leg_id))
    leg = leg_result.scalar_one_or_none()
    url = f"/escale?vessel={leg.vessel.code}&year={leg.year}&leg_id={ds.leg_id}" if leg else "/escale"
    if request.headers.get("HX-Request"):
        return HTMLResponse(content="", headers={"HX-Redirect": url})
    return RedirectResponse(url=url, status_code=303)


@router.delete("/dockers/{ds_id}", response_class=HTMLResponse)
async def docker_delete(ds_id: int, request: Request, user: User = Depends(require_permission("escale", "S")), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DockerShift).where(DockerShift.id == ds_id))
    ds = result.scalar_one_or_none()
    if not ds:
        raise HTTPException(404)
    leg_id = ds.leg_id
    await db.delete(ds)
    await db.flush()
    await log_activity(db, user, "escale", "delete", "DockerShift", ds_id, "Suppression docker shift")
    leg_result = await db.execute(select(Leg).options(selectinload(Leg.vessel)).where(Leg.id == leg_id))
    leg = leg_result.scalar_one_or_none()
    url = f"/escale?vessel={leg.vessel.code}&year={leg.year}&leg_id={leg_id}" if leg else "/escale"
    if request.headers.get("HX-Request"):
        return HTMLResponse(content="", headers={"HX-Redirect": url})
    return RedirectResponse(url=url, status_code=303)


# ═══ CREW TICKETS (billetterie transport) ═══

@router.post("/tickets/create", response_class=HTMLResponse)
async def ticket_create(
    request: Request,
    leg_id: str = Form(...),
    member_id: str = Form(...),
    ticket_type: str = Form(...),
    transport_mode: str = Form(...),
    ticket_date: str = Form(...),
    ticket_reference: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    user: User = Depends(require_permission("escale", "M")),
    db: AsyncSession = Depends(get_db),
):
    _leg_id = int(leg_id)
    _member_id = int(member_id)
    _ticket_date = date.fromisoformat(ticket_date) if ticket_date else None

    # Save file if provided
    saved_filename = None
    saved_path = None
    saved_size = None
    if file and file.filename:
        from app.utils.file_validation import validate_upload, MAX_UPLOAD_SIZE_MB
        content = await file.read()
        if len(content) > MAX_UPLOAD_SIZE_MB * 1024 * 1024:
            raise HTTPException(413, f"Fichier trop volumineux (>{MAX_UPLOAD_SIZE_MB}MB)")
        orig_name = os.path.basename(file.filename)
        ok, err = validate_upload(orig_name, content)
        if not ok:
            raise HTTPException(400, err)
        os.makedirs(TICKET_UPLOAD_DIR, exist_ok=True)
        ext = os.path.splitext(orig_name)[1].lower()
        safe_name = f"{uuid.uuid4().hex}{ext}"
        full_path = os.path.join(TICKET_UPLOAD_DIR, safe_name)
        with open(full_path, "wb") as f:
            f.write(content)
        saved_filename = orig_name
        saved_path = full_path
        saved_size = len(content)

    ticket = CrewTicket(
        member_id=_member_id, leg_id=_leg_id,
        ticket_type=ticket_type, transport_mode=transport_mode,
        ticket_date=_ticket_date,
        ticket_reference=ticket_reference.strip() if ticket_reference else None,
        filename=saved_filename, file_path=saved_path, file_size=saved_size,
        notes=notes.strip() if notes else None,
        created_by=user.full_name,
    )
    db.add(ticket)
    await db.flush()
    await log_activity(db, user, "escale", "create", "CrewTicket", ticket.id,
                        f"Billet {ticket_type} {transport_mode} pour membre #{_member_id}")

    # ── Auto-create PAF operation if foreign crew at Fécamp ──
    member_result = await db.execute(select(CrewMember).where(CrewMember.id == _member_id))
    member = member_result.scalar_one_or_none()
    leg_result = await db.execute(
        select(Leg).options(selectinload(Leg.vessel), selectinload(Leg.departure_port), selectinload(Leg.arrival_port))
        .where(Leg.id == _leg_id)
    )
    leg = leg_result.scalar_one_or_none()

    if member and member.is_foreign and leg:
        # Check if arrival port is Fécamp
        arr_locode = leg.arrival_port.locode if leg.arrival_port else ""
        if arr_locode in FECAMP_LOCODES:
            # Check if PAF operation already exists for this leg
            paf_result = await db.execute(
                select(func.count(EscaleOperation.id)).where(
                    EscaleOperation.leg_id == _leg_id,
                    EscaleOperation.action == "passage_paf",
                )
            )
            paf_count = paf_result.scalar() or 0
            if paf_count == 0:
                paf_op = EscaleOperation(
                    leg_id=_leg_id,
                    operation_type="armement",
                    action="passage_paf",
                    planned_start=leg.ata or leg.eta,
                    description=f"Passage Police Aux Frontières — Personnel étranger ({member.full_name})",
                    intervenant="PAF Fécamp",
                )
                db.add(paf_op)
                await db.flush()
                await log_activity(db, user, "escale", "create", "Operation", paf_op.id,
                                    "Auto: Passage PAF (personnel étranger à Fécamp)")

                # Create notification
                from app.models.onboard import OnboardNotification
                db.add(OnboardNotification(
                    leg_id=_leg_id, category="crew",
                    title="Passage PAF requis",
                    detail=f"Personnel étranger {member.full_name} — Fécamp — opération PAF créée automatiquement",
                ))
                await db.flush()

    # ── Check ticket date compatibility and create notification if needed ──
    if _ticket_date and leg:
        escale_start = (leg.ata or leg.eta)
        escale_end = leg.atd
        if not escale_end and escale_start:
            escale_end = escale_start + timedelta(days=leg.port_stay_days or 3)
        esc_start_date = escale_start.date() if escale_start else None
        esc_end_date = escale_end.date() if escale_end else None
        incompatible = False
        if esc_start_date and _ticket_date < esc_start_date - timedelta(days=1):
            incompatible = True
        elif esc_end_date and _ticket_date > esc_end_date + timedelta(days=1):
            incompatible = True
        if incompatible:
            from app.models.onboard import OnboardNotification
            member_name = member.full_name if member else f"Membre #{_member_id}"
            db.add(OnboardNotification(
                leg_id=_leg_id, category="crew",
                title="Billet incompatible avec les dates d'escale",
                detail=f"{member_name} — billet {transport_mode} le {_ticket_date.strftime('%d/%m/%Y')} hors fenêtre d'escale",
            ))
            await db.flush()

    url = f"/escale?vessel={leg.vessel.code}&year={leg.year}&leg_id={_leg_id}" if leg else "/escale"
    if request.headers.get("HX-Request"):
        return HTMLResponse(content="", headers={"HX-Redirect": url})
    return RedirectResponse(url=url, status_code=303)


@router.get("/tickets/{tid}/download")
async def ticket_download(tid: int, user: User = Depends(require_permission("escale", "C")), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CrewTicket).where(CrewTicket.id == tid))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(404, detail="Fichier non trouvé")
    from app.utils.safe_files import safe_file_response
    return safe_file_response(ticket.file_path, filename=ticket.filename or "ticket")


@router.delete("/tickets/{tid}", response_class=HTMLResponse)
async def ticket_delete(tid: int, request: Request, user: User = Depends(require_permission("escale", "S")), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CrewTicket).where(CrewTicket.id == tid))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(404)
    leg_id = ticket.leg_id
    # Remove file
    if ticket.file_path and os.path.isfile(ticket.file_path):
        os.remove(ticket.file_path)
    await db.delete(ticket)
    await db.flush()
    await log_activity(db, user, "escale", "delete", "CrewTicket", tid, "Suppression billet")
    leg_result = await db.execute(select(Leg).options(selectinload(Leg.vessel)).where(Leg.id == leg_id))
    leg = leg_result.scalar_one_or_none()
    url = f"/escale?vessel={leg.vessel.code}&year={leg.year}&leg_id={leg_id}" if leg else "/escale"
    if request.headers.get("HX-Request"):
        return HTMLResponse(content="", headers={"HX-Redirect": url})
    return RedirectResponse(url=url, status_code=303)
