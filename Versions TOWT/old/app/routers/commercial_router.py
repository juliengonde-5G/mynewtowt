from fastapi import APIRouter, Request, Depends, Form, HTTPException, Query, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from app.templating import templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, text
from sqlalchemy.orm import selectinload
from typing import Optional
from datetime import datetime, date
import os, shutil

from app.database import get_db
from app.auth import get_current_user
from app.permissions import require_permission
from app.models.user import User
from app.models.vessel import Vessel
from app.models.leg import Leg
from app.models.order import Order, OrderAssignment, PALETTE_FORMATS, PALETTE_COEFF
from app.models.kpi import LegKPI
from app.models.co2_variable import Co2Variable, CO2_DEFAULTS
from app.models.packing_list import PackingList, PackingListBatch
from app.models.commercial import RateGrid, RateOffer, Client as CommClient
from app.utils.activity import log_activity
from app.utils.notifications import notify_order_confirmed, notify_cargo_doc_created
from app.routers.kpi_router import compute_decarbonation, get_co2_variables

router = APIRouter(prefix="/commercial", tags=["commercial"])

DEFAULT_WEIGHT_PER_PALETTE = 0.8
UPLOAD_DIR = "app/static/uploads/orders"


def pf(val, default=None):
    if val is None or (isinstance(val, str) and val.strip() == ""): return default
    try:
        if isinstance(val, str):
            val = val.replace(" ", "").replace("\u00a0", "")
            if "." in val and "," in val: val = val.replace(".", "").replace(",", ".")
            elif "," in val: val = val.replace(",", ".")
        return float(val)
    except: return default

def pi(val, default=None):
    if val is None or (isinstance(val, str) and val.strip() == ""): return default
    try: return int(val)
    except: return default

def pd(val):
    if val is None or (isinstance(val, str) and val.strip() == ""): return None
    try: return date.fromisoformat(val)
    except: return None


async def generate_reference(db: AsyncSession) -> str:
    """F32: serialise concurrent order creations via a PG advisory lock,
    so two parallel requests cannot both see count=N and write OT-YYYY-N+1.

    pg_advisory_xact_lock is released at COMMIT (we run in a single
    transaction per request via get_db). Lock key is hashed from the
    year-prefix so different years never block each other.
    """
    year = datetime.now().year
    prefix = f"OT-{year}-"
    lock_key = hash(("commercial_ref", year)) & 0x7FFFFFFF
    await db.execute(text("SELECT pg_advisory_xact_lock(:k)").bindparams(k=lock_key))
    result = await db.execute(
        select(func.count(Order.id)).where(Order.reference.like(f"{prefix}%"))
    )
    count = result.scalar() or 0
    return f"{prefix}{count + 1:04d}"


async def find_matching_leg(db: AsyncSession, order: Order):
    if not order.departure_locode and not order.arrival_locode:
        return None
    query = select(Leg).options(
        selectinload(Leg.vessel), selectinload(Leg.departure_port), selectinload(Leg.arrival_port)
    ).where(Leg.year == datetime.now().year)
    if order.departure_locode:
        query = query.where(Leg.departure_port_locode == order.departure_locode.upper())
    if order.arrival_locode:
        query = query.where(Leg.arrival_port_locode == order.arrival_locode.upper())
    if order.delivery_date_start:
        query = query.where(or_(Leg.eta >= order.delivery_date_start, Leg.eta == None))
    query = query.order_by(Leg.eta.asc().nulls_last()).limit(1)
    result = await db.execute(query)
    return result.scalar_one_or_none()


# ─── HOME ────────────────────────────────────────────────────
@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def commercial_home(
    request: Request,
    tab: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    vessel: Optional[int] = Query(None),
    year: Optional[int] = Query(None),
    leg_id: Optional[int] = Query(None),
    user: User = Depends(require_permission("commercial", "C")),
    db: AsyncSession = Depends(get_db),
):
    active_tab = tab if tab in ("dashboard", "grids", "offers", "orders") else "dashboard"

    # ── Always needed ──
    statuses = {
        "non_affecte": "Non affecté", "reserve": "Réservé",
        "confirme": "Confirmé", "annule": "Annulé",
    }

    orders = []
    order_decarb = {}
    co2_vars = {}
    grids = []
    grid_kpis = {}
    offers = []
    kpi = {
        "total_grids_active": 0, "total_offers": 0,
        "total_offers_pending": 0, "total_offers_accepted": 0,
        "total_orders": 0, "total_ca": 0,
    }

    # ── Fetch grids (dashboard + grids tabs) ──
    if active_tab in ("dashboard", "grids"):
        grid_q = select(RateGrid).options(
            selectinload(RateGrid.client),
            selectinload(RateGrid.vessel),
            selectinload(RateGrid.lines),
        ).order_by(RateGrid.created_at.desc())
        grid_r = await db.execute(grid_q)
        grids = list(grid_r.scalars().all())

    # ── Fetch offers (dashboard + offers tabs) ──
    if active_tab in ("dashboard", "offers"):
        offer_q = select(RateOffer).options(
            selectinload(RateOffer.client),
            selectinload(RateOffer.rate_grid),
        ).order_by(RateOffer.created_at.desc())
        offer_r = await db.execute(offer_q)
        offers = list(offer_r.scalars().all())

    # ── Fetch vessels for filters ──
    vessels_result = await db.execute(select(Vessel).where(Vessel.is_active == True).order_by(Vessel.code))
    vessels = vessels_result.scalars().all()
    current_year = year or datetime.now().year
    years = list(range(datetime.now().year + 1, datetime.now().year - 3, -1))

    # ── Fetch legs for selected vessel/year ──
    filter_legs = []
    if vessel:
        v_obj = next((v for v in vessels if v.code == vessel), None)
        if v_obj:
            legs_r = await db.execute(
                select(Leg).options(selectinload(Leg.departure_port), selectinload(Leg.arrival_port))
                .where(Leg.vessel_id == v_obj.id, Leg.year == current_year)
                .order_by(Leg.sequence)
            )
            filter_legs = legs_r.scalars().all()

    # ── Fetch orders (dashboard + orders tabs) ──
    if active_tab in ("dashboard", "orders"):
        order_q = select(Order).options(
            selectinload(Order.leg).selectinload(Leg.vessel),
            selectinload(Order.leg).selectinload(Leg.arrival_port),
            selectinload(Order.rate_grid),
        ).order_by(Order.created_at.desc())
        if status:
            order_q = order_q.where(Order.status == status)
        if leg_id:
            order_q = order_q.where(Order.leg_id == leg_id)
        elif vessel:
            v_obj = next((v for v in vessels if v.code == vessel), None)
            if v_obj:
                order_q = order_q.where(Order.leg_id.in_([l.id for l in filter_legs]))
        result = await db.execute(order_q)
        orders = list(result.scalars().all())

        co2_vars = await get_co2_variables(db)
        for order in orders:
            if order.leg and order.total_weight:
                distance = order.leg.computed_distance or (
                    order.leg.distance_nm * (order.leg.elongation_coeff or 1.25) if order.leg.distance_nm else 0
                )
                decarb = compute_decarbonation(order.total_weight, distance, co2_vars)
                order_decarb[order.id] = decarb
            else:
                order_decarb[order.id] = {"decarb_t": 0, "decarb_kg": 0, "fill_rate_pct": 0}

    # ── Dashboard KPIs ──
    if active_tab == "dashboard":
        kpi["total_grids_active"] = sum(1 for g in grids if g.status == "active")
        kpi["total_offers"] = len(offers)
        kpi["total_offers_pending"] = sum(1 for o in offers if o.status in ("draft", "sent"))
        kpi["total_offers_accepted"] = sum(1 for o in offers if o.status == "accepted")
        # For orders KPI, count all orders (not just filtered)
        all_orders_r = await db.execute(select(func.count(Order.id)))
        kpi["total_orders"] = all_orders_r.scalar() or 0
        ca_r = await db.execute(select(func.coalesce(func.sum(Order.total_price), 0)))
        kpi["total_ca"] = float(ca_r.scalar() or 0)

        # Grid KPIs
        for grid in grids:
            g_offers = [o for o in offers if o.rate_grid_id == grid.id]
            g_orders_r = await db.execute(
                select(func.count(Order.id), func.coalesce(func.sum(Order.total_price), 0))
                .where(Order.rate_grid_id == grid.id)
            )
            row = g_orders_r.one()
            grid_kpis[grid.id] = {
                "nb_offers": len(g_offers),
                "nb_offers_accepted": sum(1 for o in g_offers if o.status == "accepted"),
                "nb_orders": row[0],
                "ca": float(row[1]),
            }

    return templates.TemplateResponse("commercial/index.html", {
        "request": request, "user": user,
        "active_tab": active_tab,
        "orders": orders, "statuses": statuses,
        "selected_status": status,
        "order_decarb": order_decarb,
        "co2_vars": co2_vars,
        "grids": grids,
        "grid_kpis": grid_kpis,
        "offers": offers,
        "kpi": kpi,
        "vessels": vessels,
        "selected_vessel": vessel,
        "current_year": current_year,
        "years": years,
        "legs": filter_legs,
        "leg_id": leg_id,
        "active_module": "commercial",
    })


# ─── CREATE ORDER ────────────────────────────────────────────
@router.get("/orders/create", response_class=HTMLResponse)
async def order_create_form(
    request: Request,
    user: User = Depends(require_permission("commercial", "M")),
    db: AsyncSession = Depends(get_db),
):
    ref = await generate_reference(db)
    return templates.TemplateResponse("commercial/order_form.html", {
        "request": request, "user": user,
        "edit_order": None, "reference": ref,
        "default_weight": DEFAULT_WEIGHT_PER_PALETTE,
        "palette_formats": PALETTE_FORMATS,
        "error": None,
    })

@router.post("/orders/create", response_class=HTMLResponse)
async def order_create_submit(
    request: Request,
    client_name: str = Form(...), client_contact: Optional[str] = Form(None),
    quantity_palettes: str = Form(...), palette_format: str = Form("EPAL"),
    weight_per_palette: Optional[str] = Form(None),
    unit_price: str = Form(...), thc_included: Optional[str] = Form(None),
    booking_fee: Optional[str] = Form(None), documentation_fee: Optional[str] = Form(None),
    delivery_date_start: Optional[str] = Form(None), delivery_date_end: Optional[str] = Form(None),
    departure_locode: Optional[str] = Form(None), arrival_locode: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    user: User = Depends(require_permission("commercial", "M")),
    db: AsyncSession = Depends(get_db),
):
    ref = await generate_reference(db)
    order = Order(
        reference=ref,
        client_name=client_name.strip(),
        client_contact=client_contact.strip() if client_contact else None,
        quantity_palettes=pi(quantity_palettes, 1),
        palette_format=palette_format if palette_format in PALETTE_COEFF else "EPAL",
        weight_per_palette=pf(weight_per_palette, DEFAULT_WEIGHT_PER_PALETTE),
        unit_price=pf(unit_price, 0),
        thc_included=thc_included == "on",
        booking_fee=pf(booking_fee, 0),
        documentation_fee=pf(documentation_fee, 0),
        delivery_date_start=pd(delivery_date_start),
        delivery_date_end=pd(delivery_date_end),
        departure_locode=departure_locode.strip().upper() if departure_locode and departure_locode.strip() else None,
        arrival_locode=arrival_locode.strip().upper() if arrival_locode and arrival_locode.strip() else None,
        description=description.strip() if description else None,
    )
    order.compute_total()
    db.add(order)
    await db.flush()
    await log_activity(db, user, "commercial", "create", "Order", order.id, f"Commande {order.reference}")

    # F45: auto-match no longer silently transitions status to "reserve".
    # We populate leg_id as a *suggestion* only — operator must confirm
    # via an explicit status change on the order form.
    matching = await find_matching_leg(db, order)
    if matching:
        order.leg_id = matching.id

    # ─── Push to Pipedrive as Deal ───
    try:
        from app.models.commercial import Client as CommClient
        client_r = await db.execute(
            select(CommClient).where(
                CommClient.name == order.client_name,
                CommClient.pipedrive_org_id.isnot(None),
            ).limit(1)
        )
        matched_client = client_r.scalar_one_or_none()
        if matched_client:
            from app.utils.pipedrive import create_deal
            dep = order.departure_locode or "?"
            arr = order.arrival_locode or "?"
            deal_id = await create_deal(
                title=f"OT {order.reference} — {order.client_name}",
                org_id=matched_client.pipedrive_org_id,
                value=order.total_price or 0,
                notes=(
                    f"<b>Ordre de transport {order.reference}</b><br>"
                    f"Client : {order.client_name}<br>"
                    f"Route : {dep} → {arr}<br>"
                    f"Palettes : {order.quantity_palettes} ({order.palette_format})<br>"
                    f"Prix unitaire : {order.unit_price}€<br>"
                    f"Total : {order.total_price or 0:.2f}€<br>"
                    f"Créé par {user.full_name}"
                ),
            )
            if deal_id:
                order.pipedrive_deal_id = deal_id
                await db.flush()
    except Exception as e:
        print(f"Pipedrive push error (order): {e}")

    url = "/commercial"
    if request.headers.get("HX-Request"):
        return HTMLResponse(content="", headers={"HX-Redirect": url})
    return RedirectResponse(url=url, status_code=303)


# ─── EDIT ORDER ──────────────────────────────────────────────
@router.get("/orders/{oid}/edit", response_class=HTMLResponse)
async def order_edit_form(
    oid: int, request: Request,
    user: User = Depends(require_permission("commercial", "M")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Order).where(Order.id == oid))
    order = result.scalar_one_or_none()
    if not order: raise HTTPException(404)
    return templates.TemplateResponse("commercial/order_form.html", {
        "request": request, "user": user,
        "edit_order": order, "reference": order.reference,
        "default_weight": DEFAULT_WEIGHT_PER_PALETTE,
        "palette_formats": PALETTE_FORMATS,
        "error": None,
    })

@router.post("/orders/{oid}/edit", response_class=HTMLResponse)
async def order_edit_submit(
    oid: int, request: Request,
    client_name: str = Form(...), client_contact: Optional[str] = Form(None),
    quantity_palettes: str = Form(...), palette_format: str = Form("EPAL"),
    weight_per_palette: Optional[str] = Form(None),
    unit_price: str = Form(...), thc_included: Optional[str] = Form(None),
    booking_fee: Optional[str] = Form(None), documentation_fee: Optional[str] = Form(None),
    delivery_date_start: Optional[str] = Form(None), delivery_date_end: Optional[str] = Form(None),
    departure_locode: Optional[str] = Form(None), arrival_locode: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    status: Optional[str] = Form(None),
    user: User = Depends(require_permission("commercial", "M")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Order).where(Order.id == oid))
    order = result.scalar_one_or_none()
    if not order: raise HTTPException(404)
    order.client_name = client_name.strip()
    order.client_contact = client_contact.strip() if client_contact else None
    order.quantity_palettes = pi(quantity_palettes, order.quantity_palettes)
    order.palette_format = palette_format if palette_format in PALETTE_COEFF else "EPAL"
    order.weight_per_palette = pf(weight_per_palette, DEFAULT_WEIGHT_PER_PALETTE)
    order.unit_price = pf(unit_price, order.unit_price)
    order.thc_included = thc_included == "on"
    order.booking_fee = pf(booking_fee, 0)
    order.documentation_fee = pf(documentation_fee, 0)
    order.delivery_date_start = pd(delivery_date_start)
    order.delivery_date_end = pd(delivery_date_end)
    order.departure_locode = departure_locode.strip().upper() if departure_locode and departure_locode.strip() else None
    order.arrival_locode = arrival_locode.strip().upper() if arrival_locode and arrival_locode.strip() else None
    order.description = description.strip() if description else None
    was_confirmed = order.status == "confirme"
    if status and status != order.status:
        # F46: validate order status transitions
        _ALLOWED_TRANSITIONS = {
            "brouillon":  {"brouillon", "reserve", "annule"},
            "reserve":    {"reserve", "confirme", "annule"},
            "confirme":   {"confirme", "expedie", "annule"},
            "expedie":    {"expedie", "livre"},
            "livre":      {"livre"},
            "annule":     {"annule"},
        }
        allowed = _ALLOWED_TRANSITIONS.get(order.status, set())
        if status not in allowed:
            raise HTTPException(
                400,
                f"Transition '{order.status}' → '{status}' non autorisée."
            )
        order.status = status
    order.compute_total()
    await db.flush()
    await log_activity(db, user, "commercial", "update", "Order", oid, f"Modification commande {order.reference}")

    # Workflow: when order is confirmed and has a leg assignment
    if order.status == "confirme" and not was_confirmed and order.leg_id:
        await _on_order_confirmed(db, order, user)

    url = "/commercial"
    if request.headers.get("HX-Request"):
        return HTMLResponse(content="", headers={"HX-Redirect": url})
    return RedirectResponse(url=url, status_code=303)


# ─── DELETE ORDER ────────────────────────────────────────────
@router.delete("/orders/{oid}", response_class=HTMLResponse)
async def order_delete(
    oid: int, request: Request,
    user: User = Depends(require_permission("commercial", "S")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Order).where(Order.id == oid))
    order = result.scalar_one_or_none()
    if not order: raise HTTPException(404)
    ref = order.reference
    await db.delete(order)
    await db.flush()
    await log_activity(db, user, "commercial", "delete", "Order", oid, f"Suppression commande {ref}")
    url = "/commercial"
    if request.headers.get("HX-Request"):
        return HTMLResponse(content="", headers={"HX-Redirect": url})
    return RedirectResponse(url=url, status_code=303)


# ─── ASSIGN ORDER ────────────────────────────────────────────
@router.get("/orders/{oid}/assign", response_class=HTMLResponse)
async def order_assign_form(
    oid: int, request: Request,
    user: User = Depends(require_permission("commercial", "M")),
    db: AsyncSession = Depends(get_db),
):
    order_result = await db.execute(select(Order).where(Order.id == oid))
    order = order_result.scalar_one_or_none()
    if not order: raise HTTPException(404)

    # Only show legs matching the order's route
    query = (
        select(Leg).options(
            selectinload(Leg.vessel), selectinload(Leg.departure_port), selectinload(Leg.arrival_port)
        ).where(Leg.year == datetime.now().year)
    )
    if order.departure_locode:
        query = query.where(Leg.departure_port_locode == order.departure_locode.upper())
    if order.arrival_locode:
        query = query.where(Leg.arrival_port_locode == order.arrival_locode.upper())

    query = query.order_by(Leg.vessel_id, Leg.sequence)
    result = await db.execute(query)
    legs = result.scalars().all()

    assigned_ids = {order.leg_id} if order.leg_id else set()
    suggested_leg = await find_matching_leg(db, order) if not order.leg_id else None

    return templates.TemplateResponse("commercial/assign_form.html", {
        "request": request, "user": user,
        "order": order, "legs": legs,
        "assigned_ids": assigned_ids,
        "suggested_leg": suggested_leg,
    })


@router.post("/orders/{oid}/assign", response_class=HTMLResponse)
async def order_assign_submit(
    oid: int, request: Request,
    leg_id: Optional[str] = Form(None),
    user: User = Depends(require_permission("commercial", "M")),
    db: AsyncSession = Depends(get_db),
):
    order_result = await db.execute(select(Order).where(Order.id == oid))
    order = order_result.scalar_one_or_none()
    if not order: raise HTTPException(404)

    _lid = pi(leg_id)
    order.leg_id = _lid
    if _lid:
        if order.status == "non_affecte":
            order.status = "reserve"
    else:
        order.status = "non_affecte"
    await db.flush()
    await log_activity(db, user, "commercial", "assign", "Order", oid, f"Affectation commande {order.reference}")

    url = "/commercial"
    if request.headers.get("HX-Request"):
        return HTMLResponse(content="", headers={"HX-Redirect": url})
    return RedirectResponse(url=url, status_code=303)


# ─── ATTACHMENT ──────────────────────────────────────────────
@router.post("/orders/{oid}/upload", response_class=HTMLResponse)
async def order_upload_attachment(
    oid: int, request: Request,
    file: UploadFile = File(...),
    user: User = Depends(require_permission("commercial", "M")),
    db: AsyncSession = Depends(get_db),
):
    order_result = await db.execute(select(Order).where(Order.id == oid))
    order = order_result.scalar_one_or_none()
    if not order: raise HTTPException(404)

    # Validate file type
    allowed = {".pdf", ".doc", ".docx"}
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed:
        raise HTTPException(400, detail="Format non supporté. Utilisez PDF ou Word.")

    # Save file
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    safe_name = f"order_{oid}_{int(datetime.now().timestamp())}{ext}"
    filepath = os.path.join(UPLOAD_DIR, safe_name)

    # Remove old attachment
    if order.attachment_path and os.path.exists(order.attachment_path):
        os.remove(order.attachment_path)

    with open(filepath, "wb") as f:
        content = await file.read()
        f.write(content)

    order.attachment_filename = file.filename
    order.attachment_path = filepath
    await db.flush()
    await log_activity(db, user, "commercial", "upload", "Order", oid, f"Pièce jointe commande {order.reference}")

    url = "/commercial"
    if request.headers.get("HX-Request"):
        return HTMLResponse(content="", headers={"HX-Redirect": url})
    return RedirectResponse(url=url, status_code=303)


@router.get("/orders/{oid}/attachment", response_class=FileResponse)
async def order_download_attachment(
    oid: int,
    user: User = Depends(require_permission("commercial", "C")),
    db: AsyncSession = Depends(get_db),
):
    order_result = await db.execute(select(Order).where(Order.id == oid))
    order = order_result.scalar_one_or_none()
    if not order or not order.attachment_path:
        raise HTTPException(404)
    from app.utils.safe_files import safe_file_response
    return safe_file_response(
        order.attachment_path,
        filename=order.attachment_filename,
        media_type="application/octet-stream",
    )


@router.delete("/orders/{oid}/attachment", response_class=HTMLResponse)
async def order_delete_attachment(
    oid: int, request: Request,
    user: User = Depends(require_permission("commercial", "S")),
    db: AsyncSession = Depends(get_db),
):
    order_result = await db.execute(select(Order).where(Order.id == oid))
    order = order_result.scalar_one_or_none()
    if not order: raise HTTPException(404)
    if order.attachment_path and os.path.exists(order.attachment_path):
        os.remove(order.attachment_path)
    order.attachment_filename = None
    order.attachment_path = None
    await db.flush()
    await log_activity(db, user, "commercial", "delete_attachment", "Order", oid, f"Suppression PJ commande {order.reference}")
    url = "/commercial"
    if request.headers.get("HX-Request"):
        return HTMLResponse(content="", headers={"HX-Redirect": url})
    return RedirectResponse(url=url, status_code=303)


# ─── ORDER CONFIRMATION WORKFLOW ────────────────────────────
async def _on_order_confirmed(db: AsyncSession, order: Order, user):
    """When an order is confirmed: create packing list + notify operations."""
    # 1. Check if packing list already exists
    existing = await db.execute(select(PackingList).where(PackingList.order_id == order.id))
    if existing.scalar_one_or_none():
        # Packing list already exists — just send notification
        await notify_order_confirmed(
            db, order.leg_id, order.reference, order.client_name,
            f"{order.quantity_palettes} palettes ({order.palette_format}), {order.total_weight or 0} t"
        )
        await db.flush()
        return

    # 2. Load leg with relationships for pre-fill
    leg_result = await db.execute(
        select(Leg).options(
            selectinload(Leg.vessel),
            selectinload(Leg.departure_port),
            selectinload(Leg.arrival_port),
        ).where(Leg.id == order.leg_id)
    )
    leg = leg_result.scalar_one_or_none()

    # 3. Create packing list
    pl = PackingList(order_id=order.id)
    db.add(pl)
    await db.flush()

    # 4. Create default batch pre-filled with TOWT data + order quantities
    batch = PackingListBatch(
        packing_list_id=pl.id,
        batch_number=1,
        booking_confirmation=order.reference,
        customer_name=order.client_name,
        freight_rate=order.unit_price,
        pallet_quantity=order.quantity_palettes,
        pallet_type=order.palette_format,
        weight_kg=order.weight_per_palette * 1000 if order.weight_per_palette else None,
    )
    if leg:
        batch.voyage_id = leg.leg_code
        batch.vessel = leg.vessel.name if leg.vessel else None
        batch.loading_date = leg.etd.date() if leg.etd else None
        batch.pol_code = leg.departure_port.locode if leg.departure_port else None
        batch.pod_code = leg.arrival_port.locode if leg.arrival_port else None
        batch.pol_name = leg.departure_port.name if leg.departure_port else None
        batch.pod_name = leg.arrival_port.name if leg.arrival_port else None
    db.add(batch)
    await db.flush()

    # 5. Log creation
    await log_activity(
        db, user, "cargo", "auto_create", "PackingList", pl.id,
        f"Packing list auto-créée pour commande confirmée {order.reference}"
    )

    # 6. Notify operations: order confirmed
    cargo_desc = f"{order.quantity_palettes} palettes ({order.palette_format}), {order.total_weight or 0} t"
    await notify_order_confirmed(db, order.leg_id, order.reference, order.client_name, cargo_desc)

    # 7. Notify operations: packing list created
    await notify_cargo_doc_created(db, order.leg_id, "packing_list", order.reference)
    await db.flush()
