"""
Stowage Plan Router — vessel loading plan management.

Provides endpoints for:
- Viewing/managing stowage plans per leg (escale integration)
- Auto-suggesting zone assignments for batches
- Drag & drop zone reassignment (onboard)
- Printable loading plan document (FR/EN)
- API for zone occupation data
"""

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy import select, func as sa_func
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.auth import get_current_user
from app.permissions import require_permission
from app.templating import templates
from app.models.leg import Leg
from app.models.vessel import Vessel
from app.models.order import Order, OrderAssignment
from app.models.packing_list import PackingList, PackingListBatch
from app.models.stowage import (
    StowagePlan, ZONE_DEFINITIONS, ZONE_CAPACITIES, LOADING_ORDER,
    DANGEROUS_ZONES, IMO_CLASSES, PALLET_FORMATS, PALLET_FORMAT_MAP,
    get_zone_capacity, get_zone_max_weight, get_zone_label,
    suggest_zone, must_go_sup_av, is_dangerous, is_oversized,
)

router = APIRouter(prefix="/stowage", tags=["stowage"])


# ═══════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════

async def _get_leg_with_vessel(db, leg_id: int) -> Leg:
    """Fetch leg with vessel eager-loaded."""
    result = await db.execute(
        select(Leg).options(selectinload(Leg.vessel)).where(Leg.id == leg_id)
    )
    leg = result.scalar_one_or_none()
    if not leg:
        raise HTTPException(404, "Leg introuvable")
    return leg


async def _get_leg_batches(db, leg_id: int) -> list:
    """Get all batches for orders assigned to a leg (via Order.leg_id)."""
    result = await db.execute(
        select(PackingListBatch)
        .join(PackingList, PackingListBatch.packing_list_id == PackingList.id)
        .join(Order, PackingList.order_id == Order.id)
        .where(Order.leg_id == leg_id)
        .options(selectinload(PackingListBatch.packing_list).selectinload(PackingList.order))
    )
    return result.scalars().all()


async def _get_leg_orders(db, leg_id: int) -> list:
    """Get all orders assigned to a leg (including those without packing lists)."""
    result = await db.execute(
        select(Order).where(Order.leg_id == leg_id, Order.status != "annule")
    )
    return result.scalars().all()


async def _ensure_batches_for_orders(db, leg_id: int):
    """For orders that don't have a packing list yet, create one with a placeholder batch
    using the order's palette data. This allows stowage planning before cargo docs are filled."""
    orders = await _get_leg_orders(db, leg_id)
    for order in orders:
        # Check if packing list exists
        pl_result = await db.execute(
            select(PackingList).where(PackingList.order_id == order.id)
        )
        pl = pl_result.scalar_one_or_none()
        if not pl:
            # Create packing list + batch from order data
            pl = PackingList(order_id=order.id)
            db.add(pl)
            await db.flush()

            batch = PackingListBatch(
                packing_list_id=pl.id,
                batch_number=1,
                customer_name=order.client_name,
                booking_confirmation=order.reference,
                pallet_quantity=order.quantity_palettes,
                pallet_type=order.palette_format,
                weight_kg=order.weight_per_palette * 1000 if order.weight_per_palette else None,
            )
            db.add(batch)
            await db.flush()
        else:
            # Packing list exists — check if batch has pallet data, backfill from order if not
            batches_result = await db.execute(
                select(PackingListBatch).where(PackingListBatch.packing_list_id == pl.id)
            )
            for batch in batches_result.scalars().all():
                if not batch.pallet_quantity and order.quantity_palettes:
                    batch.pallet_quantity = order.quantity_palettes
                if not batch.pallet_type and order.palette_format:
                    batch.pallet_type = order.palette_format
                if not batch.weight_kg and order.weight_per_palette:
                    batch.weight_kg = order.weight_per_palette * 1000
            await db.flush()


async def _get_stowage_plans(db, leg_id: int) -> list:
    """Get all stowage plans for a leg."""
    result = await db.execute(
        select(StowagePlan)
        .where(StowagePlan.leg_id == leg_id)
        .options(selectinload(StowagePlan.batch).selectinload(PackingListBatch.packing_list).selectinload(PackingList.order))
    )
    return result.scalars().all()


async def _get_zone_occupation(db, leg_id: int, exclude_batch_id: int = None) -> dict:
    """Calculate current zone occupation for a leg."""
    plans = await _get_stowage_plans(db, leg_id)
    occupied = {}
    for plan in plans:
        if exclude_batch_id and plan.batch_id == exclude_batch_id:
            continue
        zone = plan.zone_code
        if zone not in occupied:
            occupied[zone] = {"palettes": 0, "weight_kg": 0}
        occupied[zone]["palettes"] += (plan.pallet_quantity or 0)
        occupied[zone]["weight_kg"] += (plan.weight_total_kg or 0)
    return occupied


def _build_zone_data(plans: list, lang: str = "fr") -> dict:
    """Build zone-by-zone data structure for template rendering."""
    zones = {}
    for zone_code in LOADING_ORDER:
        zdef = ZONE_DEFINITIONS[zone_code]
        zones[zone_code] = {
            "code": zone_code,
            "label": get_zone_label(zone_code, lang),
            "deck": zdef["deck"],
            "hold": zdef["hold"],
            "block": zdef["block"],
            "surface_m2": zdef["surface_m2"],
            "resistance_t_m2": zdef["resistance_t_m2"],
            "max_weight_kg": zdef["surface_m2"] * zdef["resistance_t_m2"] * 1000,
            "batches": [],
            "total_palettes": 0,
            "total_weight_kg": 0,
            "has_dangerous": False,
        }

    for plan in plans:
        zone = plan.zone_code
        if zone not in zones:
            continue
        batch = plan.batch
        order = batch.packing_list.order if batch.packing_list else None
        zones[zone]["batches"].append({
            "plan_id": plan.id,
            "batch_id": batch.id,
            "batch_number": batch.batch_number,
            "client_name": batch.customer_name or (order.client_name if order else "—"),
            "type_of_goods": batch.type_of_goods or "—",
            "pallet_quantity": plan.pallet_quantity or 0,
            "pallet_format": plan.pallet_format or "EPAL",
            "weight_unit_kg": batch.weight_kg or 0,
            "weight_total_kg": plan.weight_total_kg or 0,
            "stackable": bool(plan.stackable),
            "is_dangerous": bool(plan.is_dangerous),
            "imo_class": plan.imo_class or "",
            "bl_number": batch.bill_of_lading_id or "—",
            "order_ref": order.reference if order else "—",
        })
        zones[zone]["total_palettes"] += (plan.pallet_quantity or 0)
        zones[zone]["total_weight_kg"] += (plan.weight_total_kg or 0)
        if plan.is_dangerous:
            zones[zone]["has_dangerous"] = True

    return zones


# ═══════════════════════════════════════════════════════════════
# MAIN STOWAGE PLAN VIEW (escale integration)
# ═══════════════════════════════════════════════════════════════

@router.get("/leg/{leg_id}")
async def stowage_plan_view(
    request: Request,
    leg_id: int,
    lang: str = "fr",
    db=Depends(get_db),
    user=Depends(require_permission("escale", "C")),
):
    """Main stowage plan page with graphical view and batch list."""
    leg = await _get_leg_with_vessel(db, leg_id)

    # Ensure all orders have batches (create placeholder from order data if needed)
    await _ensure_batches_for_orders(db, leg_id)

    plans = await _get_stowage_plans(db, leg_id)
    batches = await _get_leg_batches(db, leg_id)
    zones = _build_zone_data(plans, lang)

    # Find unassigned batches
    assigned_batch_ids = {p.batch_id for p in plans}
    unassigned = [b for b in batches if b.id not in assigned_batch_ids]

    # Calculate totals
    total_palettes = sum(z["total_palettes"] for z in zones.values())
    total_weight = sum(z["total_weight_kg"] for z in zones.values())
    total_capacity_epal = sum(
        get_zone_capacity(zc, "EPAL", False) for zc in LOADING_ORDER
    )
    fill_rate = round(total_palettes / total_capacity_epal * 100, 1) if total_capacity_epal else 0

    return templates.TemplateResponse("stowage/plan.html", {
        "request": request,
        "user": user,
        "leg": leg,
        "zones": zones,
        "zone_order": LOADING_ORDER,
        "dangerous_zones": DANGEROUS_ZONES,
        "unassigned": unassigned,
        "plans": plans,
        "total_palettes": total_palettes,
        "total_weight": total_weight,
        "fill_rate": fill_rate,
        "total_capacity": total_capacity_epal,
        "pallet_formats": PALLET_FORMATS,
        "imo_classes": IMO_CLASSES,
        "lang": lang,
        "active_module": "escale",
    })


# ═══════════════════════════════════════════════════════════════
# AUTO-ASSIGN BATCH TO ZONE
# ═══════════════════════════════════════════════════════════════

@router.post("/leg/{leg_id}/assign/{batch_id}")
async def assign_batch(
    request: Request,
    leg_id: int,
    batch_id: int,
    db=Depends(get_db),
    user=Depends(require_permission("escale", "M")),
):
    """Assign a batch to a zone (auto-suggest or manual override)."""
    form = await request.form()
    zone_code = form.get("zone_code", "").strip()

    # Get batch with its order (for fallback data)
    result = await db.execute(
        select(PackingListBatch)
        .options(selectinload(PackingListBatch.packing_list).selectinload(PackingList.order))
        .where(PackingListBatch.id == batch_id)
    )
    batch = result.scalar_one_or_none()
    if not batch:
        raise HTTPException(404, "Batch introuvable")

    # Check not already assigned
    existing = await db.execute(
        select(StowagePlan).where(
            StowagePlan.leg_id == leg_id,
            StowagePlan.batch_id == batch_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(400, "Ce batch est déjà affecté à une zone")

    # Use batch data, fallback to order data if batch not yet filled
    order = batch.packing_list.order if batch.packing_list else None
    pallet_format = batch.pallet_type or (order.palette_format if order else None) or "EPAL"
    stackable_str = (batch.stackable or "").lower()
    stackable = stackable_str in ("oui", "yes", "true", "1")
    qty = batch.pallet_quantity or (order.quantity_palettes if order else 0) or 0
    unit_weight = batch.weight_kg or (order.weight_per_palette * 1000 if order and order.weight_per_palette else 0) or 0
    weight_total = unit_weight * qty

    # Auto-suggest if no zone specified
    if not zone_code:
        occupied = await _get_zone_occupation(db, leg_id)
        zone_code = suggest_zone(batch, occupied, pallet_format)
        if not zone_code:
            raise HTTPException(400, "Aucune zone disponible pour ce batch")

    # Validate zone exists
    if zone_code not in ZONE_DEFINITIONS:
        raise HTTPException(400, f"Zone inconnue: {zone_code}")

    # Validate dangerous/oversized must go to SUP_AV
    if must_go_sup_av(batch) and zone_code not in DANGEROUS_ZONES:
        raise HTTPException(
            400,
            "Marchandise dangereuse ou hors-format : doit être placée en SUP_AV (AR/MIL/AV)"
        )

    # Validate capacity
    occupied = await _get_zone_occupation(db, leg_id)
    capacity = get_zone_capacity(zone_code, pallet_format, stackable)
    max_weight = get_zone_max_weight(zone_code) * 1000
    current = occupied.get(zone_code, {"palettes": 0, "weight_kg": 0})

    if current["palettes"] + qty > capacity:
        raise HTTPException(
            400,
            f"Capacité insuffisante dans {zone_code}: {capacity - current['palettes']} places restantes, {qty} demandées"
        )
    if current["weight_kg"] + weight_total > max_weight:
        raise HTTPException(
            400,
            f"Poids max dépassé dans {zone_code}: {(max_weight - current['weight_kg'])/1000:.1f}t restantes, {weight_total/1000:.1f}t demandées"
        )

    # Create stowage plan entry
    plan = StowagePlan(
        leg_id=leg_id,
        batch_id=batch_id,
        zone_code=zone_code,
        pallet_quantity=qty,
        pallet_format=pallet_format,
        weight_total_kg=weight_total,
        is_dangerous=1 if is_dangerous(batch.imo_product_class) else 0,
        imo_class=batch.imo_product_class,
        is_oversized=1 if is_oversized(
            batch.length_cm or 0, batch.width_cm or 0, batch.height_cm or 0
        ) else 0,
        stackable=1 if stackable else 0,
        assigned_by=user.full_name if hasattr(user, 'full_name') else user.username,
    )
    db.add(plan)
    await db.flush()

    # Also update batch.hold field for backward compatibility
    batch.hold = zone_code
    await db.flush()

    if request.headers.get("HX-Request"):
        return HTMLResponse(headers={"HX-Redirect": f"/stowage/leg/{leg_id}"})
    return RedirectResponse(f"/stowage/leg/{leg_id}", status_code=303)


# ═══════════════════════════════════════════════════════════════
# AUTO-ASSIGN ALL UNASSIGNED BATCHES
# ═══════════════════════════════════════════════════════════════

@router.post("/leg/{leg_id}/auto-assign")
async def auto_assign_all(
    request: Request,
    leg_id: int,
    db=Depends(get_db),
    user=Depends(require_permission("escale", "M")),
):
    """Auto-assign all unassigned batches to optimal zones."""
    # Ensure all orders have batches first
    await _ensure_batches_for_orders(db, leg_id)

    batches = await _get_leg_batches(db, leg_id)
    plans = await _get_stowage_plans(db, leg_id)
    assigned_ids = {p.batch_id for p in plans}
    unassigned = [b for b in batches if b.id not in assigned_ids]

    # Sort: dangerous/oversized first (they have constrained zones)
    unassigned.sort(key=lambda b: (not must_go_sup_av(b), b.id))

    occupied = await _get_zone_occupation(db, leg_id)
    assigned_count = 0
    username = user.full_name if hasattr(user, 'full_name') else user.username

    for batch in unassigned:
        # Use batch data, fallback to order data if batch not yet filled
        order = batch.packing_list.order if batch.packing_list else None
        pallet_format = batch.pallet_type or (order.palette_format if order else None) or "EPAL"
        stackable_str = (batch.stackable or "").lower()
        stackable = stackable_str in ("oui", "yes", "true", "1")
        qty = batch.pallet_quantity or (order.quantity_palettes if order else 0) or 0
        unit_weight = batch.weight_kg or (order.weight_per_palette * 1000 if order and order.weight_per_palette else 0) or 0
        weight_total = unit_weight * qty

        if qty == 0:
            continue  # Skip batches with no pallet data

        zone_code = suggest_zone(batch, occupied, pallet_format)
        if not zone_code:
            continue

        plan = StowagePlan(
            leg_id=leg_id,
            batch_id=batch.id,
            zone_code=zone_code,
            pallet_quantity=qty,
            pallet_format=pallet_format,
            weight_total_kg=weight_total,
            is_dangerous=1 if is_dangerous(batch.imo_product_class) else 0,
            imo_class=batch.imo_product_class,
            is_oversized=1 if is_oversized(
                batch.length_cm or 0, batch.width_cm or 0, batch.height_cm or 0
            ) else 0,
            stackable=1 if stackable else 0,
            assigned_by=username,
        )
        db.add(plan)

        # Update occupation tracking
        if zone_code not in occupied:
            occupied[zone_code] = {"palettes": 0, "weight_kg": 0}
        occupied[zone_code]["palettes"] += qty
        occupied[zone_code]["weight_kg"] += weight_total

        batch.hold = zone_code
        assigned_count += 1

    await db.flush()

    if request.headers.get("HX-Request"):
        return HTMLResponse(headers={"HX-Redirect": f"/stowage/leg/{leg_id}"})
    return RedirectResponse(f"/stowage/leg/{leg_id}", status_code=303)


# ═══════════════════════════════════════════════════════════════
# MOVE BATCH (drag & drop from onboard)
# ═══════════════════════════════════════════════════════════════

@router.post("/leg/{leg_id}/move/{plan_id}")
async def move_batch(
    request: Request,
    leg_id: int,
    plan_id: int,
    db=Depends(get_db),
    user=Depends(require_permission("captain", "M")),
):
    """Move a batch from one zone to another (drag & drop, silent update)."""
    form = await request.form()
    new_zone = form.get("zone_code", "").strip()

    if new_zone not in ZONE_DEFINITIONS:
        raise HTTPException(400, f"Zone inconnue: {new_zone}")

    result = await db.execute(
        select(StowagePlan)
        .options(selectinload(StowagePlan.batch))
        .where(StowagePlan.id == plan_id, StowagePlan.leg_id == leg_id)
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(404, "Affectation introuvable")

    batch = plan.batch

    # Validate dangerous/oversized constraints
    if must_go_sup_av(batch) and new_zone not in DANGEROUS_ZONES:
        raise HTTPException(400, "Marchandise dangereuse/hors-format : zone SUP_AV obligatoire")

    # Validate capacity in new zone (excluding current batch)
    occupied = await _get_zone_occupation(db, leg_id, exclude_batch_id=plan.batch_id)
    pallet_format = plan.pallet_format or "EPAL"
    stackable = bool(plan.stackable)
    capacity = get_zone_capacity(new_zone, pallet_format, stackable)
    max_weight = get_zone_max_weight(new_zone) * 1000
    current = occupied.get(new_zone, {"palettes": 0, "weight_kg": 0})

    qty = plan.pallet_quantity or 0
    weight = plan.weight_total_kg or 0

    if current["palettes"] + qty > capacity:
        raise HTTPException(400, f"Capacité insuffisante dans {new_zone}")
    if current["weight_kg"] + weight > max_weight:
        raise HTTPException(400, f"Poids max dépassé dans {new_zone}")

    # Update
    plan.zone_code = new_zone
    plan.assigned_by = user.full_name if hasattr(user, 'full_name') else user.username
    if batch:
        batch.hold = new_zone
    await db.flush()

    if request.headers.get("HX-Request"):
        return HTMLResponse("OK", status_code=200)
    return RedirectResponse(f"/stowage/leg/{leg_id}", status_code=303)


# ═══════════════════════════════════════════════════════════════
# REMOVE ASSIGNMENT
# ═══════════════════════════════════════════════════════════════

@router.post("/leg/{leg_id}/unassign/{plan_id}")
async def unassign_batch(
    request: Request,
    leg_id: int,
    plan_id: int,
    db=Depends(get_db),
    user=Depends(require_permission("escale", "M")),
):
    """Remove a batch from its zone assignment."""
    result = await db.execute(
        select(StowagePlan)
        .options(selectinload(StowagePlan.batch))
        .where(StowagePlan.id == plan_id, StowagePlan.leg_id == leg_id)
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(404, "Affectation introuvable")

    if plan.batch:
        plan.batch.hold = None
    await db.delete(plan)
    await db.flush()

    if request.headers.get("HX-Request"):
        return HTMLResponse(headers={"HX-Redirect": f"/stowage/leg/{leg_id}"})
    return RedirectResponse(f"/stowage/leg/{leg_id}", status_code=303)


# ═══════════════════════════════════════════════════════════════
# PRINTABLE LOADING PLAN (FR/EN)
# ═══════════════════════════════════════════════════════════════

@router.get("/leg/{leg_id}/print")
async def print_loading_plan(
    request: Request,
    leg_id: int,
    lang: str = "fr",
    db=Depends(get_db),
    user=Depends(require_permission("escale", "C")),
):
    """Printable A4 loading plan with vessel schematic and batch detail table."""
    leg = await _get_leg_with_vessel(db, leg_id)
    plans = await _get_stowage_plans(db, leg_id)
    zones = _build_zone_data(plans, lang)

    total_palettes = sum(z["total_palettes"] for z in zones.values())
    total_weight = sum(z["total_weight_kg"] for z in zones.values())
    total_capacity = sum(get_zone_capacity(zc, "EPAL", False) for zc in LOADING_ORDER)
    fill_rate = round(total_palettes / total_capacity * 100, 1) if total_capacity else 0

    # Flatten batches for detail table
    all_batches = []
    for zone_code in LOADING_ORDER:
        zone = zones[zone_code]
        for b in zone["batches"]:
            b["zone_code"] = zone_code
            b["zone_label"] = zone["label"]
            all_batches.append(b)

    return templates.TemplateResponse("stowage/print.html", {
        "request": request,
        "user": user,
        "leg": leg,
        "zones": zones,
        "zone_order": LOADING_ORDER,
        "dangerous_zones": DANGEROUS_ZONES,
        "all_batches": all_batches,
        "total_palettes": total_palettes,
        "total_weight": total_weight,
        "fill_rate": fill_rate,
        "total_capacity": total_capacity,
        "lang": lang,
        "active_module": "escale",
    })


# ═══════════════════════════════════════════════════════════════
# ONBOARD STOWAGE VIEW (with drag & drop)
# ═══════════════════════════════════════════════════════════════

@router.get("/onboard/{leg_id}")
async def onboard_stowage_view(
    request: Request,
    leg_id: int,
    db=Depends(get_db),
    user=Depends(require_permission("captain", "C")),
):
    """Onboard stowage view with drag & drop capability."""
    leg = await _get_leg_with_vessel(db, leg_id)
    plans = await _get_stowage_plans(db, leg_id)
    zones = _build_zone_data(plans, "fr")

    total_palettes = sum(z["total_palettes"] for z in zones.values())
    total_capacity = sum(get_zone_capacity(zc, "EPAL", False) for zc in LOADING_ORDER)
    fill_rate = round(total_palettes / total_capacity * 100, 1) if total_capacity else 0

    return templates.TemplateResponse("stowage/onboard.html", {
        "request": request,
        "user": user,
        "leg": leg,
        "zones": zones,
        "zone_order": LOADING_ORDER,
        "dangerous_zones": DANGEROUS_ZONES,
        "total_palettes": total_palettes,
        "fill_rate": fill_rate,
        "active_module": "captain",
    })


# ═══════════════════════════════════════════════════════════════
# API: Zone occupation data (JSON for client extranet)
# ═══════════════════════════════════════════════════════════════

@router.get("/api/leg/{leg_id}/zones")
async def api_zone_data(
    leg_id: int,
    db=Depends(get_db),
    user=Depends(require_permission("escale", "C")),
):
    """API endpoint returning zone occupation data as JSON."""
    plans = await _get_stowage_plans(db, leg_id)
    zones = _build_zone_data(plans)
    return {
        "zones": zones,
        "zone_order": LOADING_ORDER,
        "dangerous_zones": DANGEROUS_ZONES,
    }


@router.get("/api/leg/{leg_id}/batch/{batch_id}/position")
async def api_batch_position(
    leg_id: int,
    batch_id: int,
    db=Depends(get_db),
):
    """Get the current zone position of a batch (used by claims and client portal)."""
    result = await db.execute(
        select(StowagePlan).where(
            StowagePlan.leg_id == leg_id,
            StowagePlan.batch_id == batch_id,
        )
    )
    plan = result.scalar_one_or_none()
    if not plan:
        return {"zone_code": None, "zone_label": None}
    return {
        "zone_code": plan.zone_code,
        "zone_label_fr": get_zone_label(plan.zone_code, "fr"),
        "zone_label_en": get_zone_label(plan.zone_code, "en"),
    }
