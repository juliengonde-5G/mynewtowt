from fastapi import APIRouter, Request, Depends, Form, HTTPException, Query, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from app.templating import templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
from typing import Optional
from datetime import datetime, date, timedelta
import io
import os
import uuid

from app.database import get_db
from app.auth import get_current_user
from app.permissions import require_permission
from app.models.user import User
from app.models.vessel import Vessel
from app.models.leg import Leg
from app.models.crew import CrewMember, CrewAssignment, CrewTicket, CREW_ROLES, REQUIRED_ROLES, TRANSPORT_MODES
from app.models.operation import EscaleOperation
from app.utils.activity import log_activity

TICKET_UPLOAD_DIR = "/app/uploads/crew_tickets"
FECAMP_LOCODES = {"FRFEC"}

router = APIRouter(prefix="/crew", tags=["crew"])


def parse_date(val):
    if val is None or (isinstance(val, str) and val.strip() == ""):
        return None
    # F5: narrow bare `except:` — only swallow date-parsing errors,
    # not SystemExit / KeyboardInterrupt / bugs
    try:
        return date.fromisoformat(val)
    except (ValueError, TypeError):
        return None


# ─── CREW LIST ───────────────────────────────────────────────
@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def crew_list(
    request: Request,
    role: Optional[str] = Query(None),
    vessel: Optional[int] = Query(None),
    user: User = Depends(require_permission("crew", "C")),
    db: AsyncSession = Depends(get_db),
):
    query = select(CrewMember).options(
        selectinload(CrewMember.assignments).selectinload(CrewAssignment.vessel)
    )
    if role:
        query = query.where(CrewMember.role == role)
    query = query.order_by(CrewMember.role, CrewMember.last_name)
    result = await db.execute(query)
    members = result.scalars().all()

    vessels_result = await db.execute(select(Vessel).where(Vessel.is_active == True).order_by(Vessel.code))
    vessels = vessels_result.scalars().all()

    today = date.today()

    # Compute status for each member
    member_data = []
    for m in members:
        current_assignment = None
        for a in m.assignments:
            if a.embark_date <= today and (a.disembark_date is None or a.disembark_date >= today):
                current_assignment = a
                break
        status = "repos"
        location = ""
        if current_assignment:
            status = "active"
            location = current_assignment.vessel.name if current_assignment.vessel else ""
        member_data.append({
            "member": m,
            "status": status,
            "location": location,
            "current_assignment": current_assignment,
            "current_assignment_id": current_assignment.id if current_assignment else None,
            "total_days_year": sum(
                ((a.disembark_date or today) - a.embark_date).days
                for a in m.assignments
                if a.embark_date.year == today.year
            ),
        })

    # Bordée par navire
    bordees = {}
    for v in vessels:
        crew_on_board = []
        for md in member_data:
            if md["current_assignment"] and md["current_assignment"].vessel_id == v.id:
                crew_on_board.append(md)
        bordees[v.name] = {
            "vessel": v,
            "crew": crew_on_board,
            "missing": [r for r in REQUIRED_ROLES if not any(
                md["member"].role == r for md in crew_on_board
            )],
        }

    stats = {
        "total": len(members),
        "active": sum(1 for md in member_data if md["status"] == "active"),
        "repos": sum(1 for md in member_data if md["status"] == "repos"),
    }

    # Compliance alerts for banner
    compliance_alerts = []
    for m in members:
        if m.passport_expiry and (m.passport_expiry - today).days < 30:
            compliance_alerts.append(m)
        elif m.visa_expiry and (m.visa_expiry - today).days < 30:
            compliance_alerts.append(m)

    # Load legs for ticket form (current year, all vessels)
    current_year = today.year
    legs_result = await db.execute(
        select(Leg).options(
            selectinload(Leg.vessel), selectinload(Leg.departure_port), selectinload(Leg.arrival_port)
        ).where(Leg.year == current_year).order_by(Leg.vessel_id, Leg.sequence)
    )
    legs = legs_result.scalars().all()

    # Load recent crew tickets (last 50)
    tickets_result = await db.execute(
        select(CrewTicket).options(
            selectinload(CrewTicket.member), selectinload(CrewTicket.leg)
        ).order_by(CrewTicket.created_at.desc()).limit(50)
    )
    crew_tickets = tickets_result.scalars().all()

    return templates.TemplateResponse("crew/index.html", {
        "request": request, "user": user,
        "member_data": member_data,
        "bordees": bordees,
        "vessels": vessels,
        "stats": stats,
        "crew_roles": CREW_ROLES,
        "current_role": role,
        "current_year": current_year,
        "compliance_alerts": compliance_alerts,
        "legs": legs,
        "crew_tickets": crew_tickets,
        "transport_modes": TRANSPORT_MODES,
        "active_module": "crew",
    })


# ─── CREATE MEMBER ───────────────────────────────────────────
@router.get("/members/create", response_class=HTMLResponse)
async def member_create_form(request: Request, user: User = Depends(require_permission("crew", "M"))):
    return templates.TemplateResponse("crew/member_form.html", {
        "request": request, "user": user,
        "edit_member": None, "crew_roles": CREW_ROLES, "error": None,
    })


@router.post("/members/create", response_class=HTMLResponse)
async def member_create_submit(
    request: Request,
    first_name: str = Form(...), last_name: str = Form(...),
    role: str = Form(...),
    phone: Optional[str] = Form(None), email: Optional[str] = Form(None),
    is_foreign: Optional[str] = Form(None),
    nationality: Optional[str] = Form(None),
    passport_number: Optional[str] = Form(None),
    passport_expiry: Optional[str] = Form(None),
    visa_type: Optional[str] = Form(None),
    visa_expiry: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    user: User = Depends(require_permission("crew", "M")),
    db: AsyncSession = Depends(get_db),
):
    member = CrewMember(
        first_name=first_name.strip(), last_name=last_name.strip(),
        role=role, phone=phone, email=email,
        is_foreign=bool(is_foreign),
        nationality=nationality.strip() if nationality else None,
        passport_number=passport_number.strip() if passport_number else None,
        passport_expiry=parse_date(passport_expiry),
        visa_type=visa_type.strip() if visa_type else None,
        visa_expiry=parse_date(visa_expiry),
        notes=notes.strip() if notes else None,
    )
    db.add(member)
    await db.flush()
    await log_activity(db, user, "crew", "create", "CrewMember", member.id, f"Marin {member.first_name} {member.last_name}")
    if request.headers.get("HX-Request"):
        return HTMLResponse(content="", headers={"HX-Redirect": "/crew"})
    return RedirectResponse(url="/crew", status_code=303)


# ─── EDIT MEMBER ─────────────────────────────────────────────
@router.get("/members/{mid}/edit", response_class=HTMLResponse)
async def member_edit_form(
    mid: int, request: Request,
    user: User = Depends(require_permission("crew", "M")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(CrewMember).where(CrewMember.id == mid))
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse("crew/member_form.html", {
        "request": request, "user": user,
        "edit_member": member, "crew_roles": CREW_ROLES, "error": None,
    })


@router.post("/members/{mid}/edit", response_class=HTMLResponse)
async def member_edit_submit(
    mid: int, request: Request,
    first_name: str = Form(...), last_name: str = Form(...),
    role: str = Form(...),
    phone: Optional[str] = Form(None), email: Optional[str] = Form(None),
    is_foreign: Optional[str] = Form(None),
    nationality: Optional[str] = Form(None),
    passport_number: Optional[str] = Form(None),
    passport_expiry: Optional[str] = Form(None),
    visa_type: Optional[str] = Form(None),
    visa_expiry: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    user: User = Depends(require_permission("crew", "M")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(CrewMember).where(CrewMember.id == mid))
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404)
    member.first_name = first_name.strip()
    member.last_name = last_name.strip()
    member.role = role
    member.phone = phone
    member.email = email
    member.is_foreign = bool(is_foreign)
    member.nationality = nationality.strip() if nationality else None
    member.passport_number = passport_number.strip() if passport_number else None
    member.passport_expiry = parse_date(passport_expiry)
    member.visa_type = visa_type.strip() if visa_type else None
    member.visa_expiry = parse_date(visa_expiry)
    member.notes = notes.strip() if notes else None
    await db.flush()
    await log_activity(db, user, "crew", "update", "CrewMember", mid, f"Modification marin {member.first_name} {member.last_name}")
    if request.headers.get("HX-Request"):
        return HTMLResponse(content="", headers={"HX-Redirect": "/crew"})
    return RedirectResponse(url="/crew", status_code=303)


# ─── DELETE MEMBER ───────────────────────────────────────────
@router.delete("/members/{mid}", response_class=HTMLResponse)
async def member_delete(
    mid: int, request: Request,
    user: User = Depends(require_permission("crew", "S")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(CrewMember).where(CrewMember.id == mid))
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404)
    name = f"{member.first_name} {member.last_name}"
    await db.delete(member)
    await db.flush()
    await log_activity(db, user, "crew", "delete", "CrewMember", mid, f"Suppression marin {name}")
    if request.headers.get("HX-Request"):
        return HTMLResponse(content="", headers={"HX-Redirect": "/crew"})
    return RedirectResponse(url="/crew", status_code=303)


# ─── ASSIGNMENTS ─────────────────────────────────────────────
@router.get("/members/{mid}/assign", response_class=HTMLResponse)
async def assign_form(
    mid: int, request: Request,
    user: User = Depends(require_permission("crew", "M")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(CrewMember).where(CrewMember.id == mid))
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404)
    vessels_result = await db.execute(select(Vessel).where(Vessel.is_active == True).order_by(Vessel.code))
    vessels = vessels_result.scalars().all()
    return templates.TemplateResponse("crew/assign_form.html", {
        "request": request, "user": user,
        "member": member, "vessels": vessels, "error": None,
    })


@router.post("/members/{mid}/assign", response_class=HTMLResponse)
async def assign_submit(
    mid: int, request: Request,
    vessel_id: str = Form(...),
    embark_date: str = Form(...),
    disembark_date: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    user: User = Depends(require_permission("crew", "M")),
    db: AsyncSession = Depends(get_db),
):
    _vessel_id = int(vessel_id)
    _embark = parse_date(embark_date)
    _disembark = parse_date(disembark_date)

    # F28: embark <= disembark
    if _embark and _disembark and _embark > _disembark:
        raise HTTPException(400, "La date d'embarquement doit être antérieure à la date de débarquement.")

    # F6: reject overlapping assignments for the same crew member
    # (already on another vessel over the same period).
    overlap_q = (
        select(CrewAssignment)
        .where(CrewAssignment.member_id == mid)
        .where(CrewAssignment.embark_date <= (_disembark or date.max))
        .where(
            (CrewAssignment.disembark_date == None) |
            (CrewAssignment.disembark_date >= (_embark or date.min))
        )
    )
    overlap_r = await db.execute(overlap_q)
    if overlap_r.scalars().first() is not None:
        raise HTTPException(
            400,
            "Ce marin est déjà affecté sur la période demandée. "
            "Clôturez l'affectation existante avant d'en créer une nouvelle."
        )

    # F29: compute status by comparison with today, not by presence
    # of disembark_date.
    today = date.today()
    if _embark and _embark > today:
        _status = "planned"
    elif _disembark and _disembark < today:
        _status = "completed"
    else:
        _status = "active"

    assignment = CrewAssignment(
        member_id=mid, vessel_id=_vessel_id,
        embark_date=_embark,
        disembark_date=_disembark,
        status=_status,
        notes=notes.strip() if notes else None,
    )
    db.add(assignment)
    await db.flush()
    await log_activity(db, user, "crew", "assign", "CrewAssignment", assignment.id, f"Affectation marin")
    if request.headers.get("HX-Request"):
        return HTMLResponse(content="", headers={"HX-Redirect": "/crew"})
    return RedirectResponse(url="/crew", status_code=303)


# ─── EDIT ASSIGNMENT (embark/disembark dates) ───────────────
@router.get("/assignments/{aid}/edit", response_class=HTMLResponse)
async def assignment_edit_form(
    aid: int, request: Request,
    user: User = Depends(require_permission("crew", "M")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CrewAssignment)
        .options(selectinload(CrewAssignment.member), selectinload(CrewAssignment.vessel))
        .where(CrewAssignment.id == aid)
    )
    assignment = result.scalar_one_or_none()
    if not assignment:
        raise HTTPException(404)
    vessels_result = await db.execute(select(Vessel).where(Vessel.is_active == True).order_by(Vessel.code))
    vessels = vessels_result.scalars().all()
    return templates.TemplateResponse("crew/assignment_edit.html", {
        "request": request, "user": user,
        "assignment": assignment, "vessels": vessels,
    })


@router.post("/assignments/{aid}/edit", response_class=HTMLResponse)
async def assignment_edit_submit(
    aid: int, request: Request,
    vessel_id: str = Form(...),
    embark_date: str = Form(...),
    disembark_date: Optional[str] = Form(None),
    status: str = Form("active"),
    notes: Optional[str] = Form(None),
    user: User = Depends(require_permission("crew", "M")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(CrewAssignment).where(CrewAssignment.id == aid))
    assignment = result.scalar_one_or_none()
    if not assignment:
        raise HTTPException(404)
    assignment.vessel_id = int(vessel_id)
    assignment.embark_date = parse_date(embark_date)
    assignment.disembark_date = parse_date(disembark_date)
    assignment.status = status
    assignment.notes = notes.strip() if notes else None
    await db.flush()
    await log_activity(db, user, "crew", "update", "CrewAssignment", aid, f"Modification affectation")
    if request.headers.get("HX-Request"):
        return HTMLResponse(content="", headers={"HX-Redirect": "/crew"})
    return RedirectResponse(url="/crew", status_code=303)


@router.delete("/assignments/{aid}", response_class=HTMLResponse)
async def assignment_delete(
    aid: int, request: Request,
    user: User = Depends(require_permission("crew", "S")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(CrewAssignment).where(CrewAssignment.id == aid))
    assignment = result.scalar_one_or_none()
    if not assignment:
        raise HTTPException(status_code=404)
    await db.delete(assignment)
    await db.flush()
    await log_activity(db, user, "crew", "delete", "CrewAssignment", aid, "Suppression affectation")
    if request.headers.get("HX-Request"):
        return HTMLResponse(content="", headers={"HX-Redirect": "/crew"})
    return RedirectResponse(url="/crew", status_code=303)


# ─── API: Get crew members for a vessel (for operation forms) ──
@router.get("/api/vessel/{vessel_id}", response_class=HTMLResponse)
async def crew_for_vessel_api(
    vessel_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_permission("crew", "C")),
):
    """Return crew members currently on board a vessel (for embark/disembark selection)."""
    from fastapi.responses import JSONResponse
    today = date.today()
    result = await db.execute(
        select(CrewAssignment).options(selectinload(CrewAssignment.member))
        .where(
            CrewAssignment.vessel_id == vessel_id,
            CrewAssignment.embark_date <= today,
            (CrewAssignment.disembark_date == None) | (CrewAssignment.disembark_date >= today),
        )
    )
    assignments = result.scalars().all()
    members = [
        {"id": a.member.id, "name": a.member.full_name, "role": a.member.role_label}
        for a in assignments if a.member
    ]
    # Also get all active members not on board (for embarkation)
    all_result = await db.execute(
        select(CrewMember).where(CrewMember.is_active == True).order_by(CrewMember.role, CrewMember.last_name)
    )
    all_members = all_result.scalars().all()
    on_board_ids = {a.member_id for a in assignments}
    available = [
        {"id": m.id, "name": m.full_name, "role": m.role_label}
        for m in all_members if m.id not in on_board_ids
    ]
    return JSONResponse({"on_board": members, "available": available})


# ─── MEMBER CALENDAR ─────────────────────────────────────────
@router.get("/members/{mid}/calendar", response_class=HTMLResponse)
async def member_calendar(
    mid: int, request: Request,
    year: Optional[int] = Query(None),
    user: User = Depends(require_permission("crew", "C")),
    db: AsyncSession = Depends(get_db),
):
    current_year = year or date.today().year
    result = await db.execute(
        select(CrewMember).options(
            selectinload(CrewMember.assignments).selectinload(CrewAssignment.vessel)
        ).where(CrewMember.id == mid)
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404)

    # Filter assignments for the year
    year_assignments = [
        a for a in member.assignments
        if a.embark_date.year == current_year or
           (a.disembark_date and a.disembark_date.year == current_year) or
           (a.embark_date.year <= current_year and (a.disembark_date is None or a.disembark_date.year >= current_year))
    ]
    year_assignments.sort(key=lambda a: a.embark_date)

    today = date.today()
    total_days = sum(
        ((min(a.disembark_date or today, date(current_year, 12, 31)) -
          max(a.embark_date, date(current_year, 1, 1))).days + 1)
        for a in year_assignments
        if a.embark_date <= date(current_year, 12, 31) and
           (a.disembark_date is None or a.disembark_date >= date(current_year, 1, 1))
    )
    days_in_year = 366 if current_year % 4 == 0 else 365
    rest_days = days_in_year - total_days

    # Load crew tickets for this member
    tickets_result = await db.execute(
        select(CrewTicket).options(selectinload(CrewTicket.leg))
        .where(CrewTicket.member_id == mid)
        .order_by(CrewTicket.ticket_date.desc())
    )
    crew_tickets = tickets_result.scalars().all()

    return templates.TemplateResponse("crew/calendar.html", {
        "request": request, "user": user,
        "member": member, "assignments": year_assignments,
        "crew_tickets": crew_tickets,
        "current_year": current_year,
        "total_days": total_days, "rest_days": rest_days,
        "days_in_year": days_in_year, "today": today,
        "active_module": "crew",
    })


# ─── COMPLIANCE DASHBOARD ────────────────────────────────────
@router.get("/compliance", response_class=HTMLResponse)
async def crew_compliance(
    request: Request,
    user: User = Depends(require_permission("crew", "C")),
    db: AsyncSession = Depends(get_db),
):
    """Dashboard showing visa/passport expiry alerts and foreign crew compliance."""
    result = await db.execute(
        select(CrewMember).where(CrewMember.is_active == True)
        .order_by(CrewMember.role, CrewMember.last_name)
    )
    members = result.scalars().all()

    today = date.today()
    alerts = []
    foreign_crew = []

    for m in members:
        if m.is_foreign:
            foreign_crew.append(m)
        # Passport alerts
        if m.passport_expiry:
            days = (m.passport_expiry - today).days
            if days < 0:
                alerts.append({"member": m, "type": "passport", "severity": "expired", "days": days,
                               "message": f"Passeport expiré depuis {abs(days)} jours"})
            elif days < 30:
                alerts.append({"member": m, "type": "passport", "severity": "warning", "days": days,
                               "message": f"Passeport expire dans {days} jours"})
        # Visa alerts
        if m.visa_expiry:
            days = (m.visa_expiry - today).days
            if days < 0:
                alerts.append({"member": m, "type": "visa", "severity": "expired", "days": days,
                               "message": f"Visa expiré depuis {abs(days)} jours"})
            elif days < 30:
                alerts.append({"member": m, "type": "visa", "severity": "warning", "days": days,
                               "message": f"Visa expire dans {days} jours"})
        # Missing passport for foreign crew
        if m.is_foreign and not m.passport_number:
            alerts.append({"member": m, "type": "missing", "severity": "warning", "days": 0,
                           "message": "N° passeport manquant"})

    alerts.sort(key=lambda a: a["days"])

    stats = {
        "total_foreign": len(foreign_crew),
        "expired": sum(1 for a in alerts if a["severity"] == "expired"),
        "warnings": sum(1 for a in alerts if a["severity"] == "warning"),
        "compliant": len([m for m in foreign_crew if m.compliance_status == "ok"]),
    }

    return templates.TemplateResponse("crew/compliance.html", {
        "request": request, "user": user,
        "alerts": alerts, "foreign_crew": foreign_crew,
        "stats": stats, "today": today,
        "active_module": "crew",
    })


# ─── BORDER POLICE CREW LIST (PDF) ───────────────────────────
@router.get("/border-police/{vessel_id}", response_class=HTMLResponse)
async def border_police_export(
    vessel_id: int, request: Request,
    user: User = Depends(require_permission("crew", "C")),
    db: AsyncSession = Depends(get_db),
):
    """Generate crew manifest PDF for border police."""
    from fastapi.responses import Response
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm

    vessel_result = await db.execute(select(Vessel).where(Vessel.id == vessel_id))
    vessel = vessel_result.scalar_one_or_none()
    if not vessel:
        raise HTTPException(404)

    today = date.today()
    result = await db.execute(
        select(CrewAssignment).options(selectinload(CrewAssignment.member))
        .where(
            CrewAssignment.vessel_id == vessel_id,
            CrewAssignment.embark_date <= today,
            (CrewAssignment.disembark_date == None) | (CrewAssignment.disembark_date >= today),
        )
    )
    assignments = result.scalars().all()

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), topMargin=20*mm, bottomMargin=15*mm)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("Title", parent=styles["Heading1"], fontName="Helvetica-Bold",
                                  fontSize=16, alignment=1, spaceAfter=6)
    sub_style = ParagraphStyle("Sub", parent=styles["Normal"], fontName="Helvetica",
                                fontSize=10, alignment=1, spaceAfter=12, textColor=colors.grey)

    elements = [
        Paragraph("CREW LIST / LISTE D'ÉQUIPAGE", title_style),
        Paragraph(f"Vessel: {vessel.name} ({vessel.code}) — Date: {today.strftime('%d/%m/%Y')}", sub_style),
        Spacer(1, 6*mm),
    ]

    # Table headers
    header = ["#", "Nom / Name", "Prénom / First Name", "Rôle / Role", "Nationalité",
              "N° Passeport", "Exp. Passeport", "Visa", "Exp. Visa", "Embarquement"]
    data = [header]
    for i, a in enumerate(assignments, 1):
        m = a.member
        data.append([
            str(i), m.last_name, m.first_name, m.role_label,
            m.nationality or "—",
            m.passport_number or "—",
            m.passport_expiry.strftime("%d/%m/%Y") if m.passport_expiry else "—",
            (m.visa_type or "—").upper(),
            m.visa_expiry.strftime("%d/%m/%Y") if m.visa_expiry else "—",
            a.embark_date.strftime("%d/%m/%Y"),
        ])

    col_widths = [20, 80, 80, 70, 60, 70, 60, 50, 60, 60]
    table = Table(data, colWidths=[w*mm/3 for w in col_widths])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#095561")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 7),
        ("FONTSIZE", (0, 1), (-1, -1), 7),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafb")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    elements.append(table)

    # Footer with count
    elements.append(Spacer(1, 8*mm))
    elements.append(Paragraph(f"Total: {len(assignments)} crew members on board", sub_style))
    elements.append(Paragraph(f"Foreign nationals: {sum(1 for a in assignments if a.member.is_foreign)}", sub_style))

    doc.build(elements)
    buf.seek(0)
    filename = f"CrewList_{vessel.code}_{today.strftime('%Y%m%d')}.pdf"

    await log_activity(db, user=user, action="export", module="crew",
                       entity_type="border_police", entity_id=vessel_id,
                       entity_label=f"Export liste équipage {vessel.name}")

    return Response(content=buf.read(), media_type="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename={filename}"})


# ─── BILLETTERIE ÉQUIPAGE ───────────────────────────────────

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
    user: User = Depends(require_permission("crew", "M")),
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
    await log_activity(db, user, "crew", "create", "CrewTicket", ticket.id,
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
        arr_locode = leg.arrival_port.locode if leg.arrival_port else ""
        if arr_locode in FECAMP_LOCODES:
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
                await log_activity(db, user, "crew", "create", "Operation", paf_op.id,
                                    "Auto: Passage PAF (personnel étranger à Fécamp)")

                from app.models.onboard import OnboardNotification
                db.add(OnboardNotification(
                    leg_id=_leg_id, category="crew",
                    title="Passage PAF requis",
                    detail=f"Personnel étranger {member.full_name} — Fécamp — opération PAF créée automatiquement",
                ))
                await db.flush()

    # ── Check ticket date compatibility ──
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

    if request.headers.get("HX-Request"):
        return HTMLResponse(content="", headers={"HX-Redirect": "/crew"})
    return RedirectResponse(url="/crew", status_code=303)


@router.get("/tickets/{tid}/download")
async def ticket_download(tid: int, user: User = Depends(require_permission("crew", "C")), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CrewTicket).where(CrewTicket.id == tid))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(404, detail="Fichier non trouvé")
    from app.utils.safe_files import safe_file_response
    return safe_file_response(ticket.file_path, filename=ticket.filename or "ticket")


@router.delete("/tickets/{tid}", response_class=HTMLResponse)
async def ticket_delete(tid: int, request: Request, user: User = Depends(require_permission("crew", "S")), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CrewTicket).where(CrewTicket.id == tid))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(404)
    if ticket.file_path and os.path.isfile(ticket.file_path):
        os.remove(ticket.file_path)
    await db.delete(ticket)
    await db.flush()
    await log_activity(db, user, "crew", "delete", "CrewTicket", tid, "Suppression billet")
    if request.headers.get("HX-Request"):
        return HTMLResponse(content="", headers={"HX-Redirect": "/crew"})
    return RedirectResponse(url="/crew", status_code=303)
