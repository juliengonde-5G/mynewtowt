from fastapi import APIRouter, Request, Depends, Form, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from app.templating import templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import Optional
from datetime import datetime
import csv
import io

from app.database import get_db
from app.auth import get_current_user
from app.permissions import require_permission
from app.models.user import User
from app.models.vessel import Vessel
from app.models.leg import Leg
from app.models.order import Order, OrderAssignment
from app.models.finance import LegFinance, PortConfig, OpexParameter
from app.utils.activity import log_activity

router = APIRouter(prefix="/finance", tags=["finance"])

OPEX_DAILY_DEFAULT = 11600


def pf(val, default=0):
    """Parse float, accepting both . and , as decimal separator."""
    if val is None or (isinstance(val, str) and val.strip() == ""):
        return default
    try:
        if isinstance(val, str):
            val = val.replace(" ", "").replace("\u00a0", "")
            # If both . and , present: 1.234,56 → 1234.56
            if "." in val and "," in val:
                val = val.replace(".", "").replace(",", ".")
            elif "," in val:
                val = val.replace(",", ".")
        return float(val)
    except (ValueError, TypeError):
        return default



# Register Jinja2 filter


async def get_opex_daily(db: AsyncSession) -> float:
    result = await db.execute(
        select(OpexParameter).where(OpexParameter.parameter_name == "opex_daily_rate")
    )
    param = result.scalar_one_or_none()
    return param.parameter_value if param else OPEX_DAILY_DEFAULT


async def compute_revenue_from_orders(db: AsyncSession, leg_id: int) -> float:
    result = await db.execute(
        select(OrderAssignment).options(selectinload(OrderAssignment.order))
        .where(OrderAssignment.leg_id == leg_id)
    )
    total = 0
    for a in result.scalars().all():
        if a.order and a.order.total_price:
            total += a.order.total_price
    return round(total, 2)


async def compute_pax_revenue_for_leg(db: AsyncSession, leg_id: int) -> float:
    """Passenger activity removed in v3.0.0. Stub kept to avoid touching every
    caller and template; always returns 0.0."""
    return 0.0


async def compute_palettes_for_leg(db: AsyncSession, leg_id: int) -> int:
    result = await db.execute(
        select(OrderAssignment).options(selectinload(OrderAssignment.order))
        .where(OrderAssignment.leg_id == leg_id)
    )
    total = 0
    for a in result.scalars().all():
        if a.order:
            total += a.order.quantity_palettes or 0
    return total


async def get_port_config(db: AsyncSession, locode: str) -> Optional[PortConfig]:
    result = await db.execute(select(PortConfig).where(PortConfig.port_locode == locode))
    return result.scalar_one_or_none()


async def compute_defaults_for_leg(db: AsyncSession, leg) -> dict:
    opex_daily = await get_opex_daily(db)

    # OPEX mer
    sea_days = (leg.estimated_duration_hours or 0) / 24
    opex_forecast = round(opex_daily * sea_days, 0)

    # Port costs + quay from arrival port config
    arr_config = await get_port_config(db, leg.arrival_port_locode)
    port_cost = arr_config.port_cost_total if arr_config else 0
    daily_quay = arr_config.daily_quay_cost if arr_config else 0

    # Quay cost = daily_quay × port_stay_days
    quay_days = leg.port_stay_days or 3
    quay_cost = round(daily_quay * quay_days, 0)

    # Ops cost = palettes × cost_per_palette
    palettes = await compute_palettes_for_leg(db, leg.id)
    cost_palette = arr_config.cost_per_palette if arr_config else 0
    ops_cost = round(palettes * cost_palette, 0)

    return {
        "sea_f": opex_forecast,
        "port_f": port_cost,
        "quay_f": quay_cost,
        "quay_days": quay_days,
        "daily_quay": daily_quay,
        "ops_f": ops_cost,
    }


async def get_or_create_finance(db: AsyncSession, leg_id: int) -> LegFinance:
    result = await db.execute(select(LegFinance).where(LegFinance.leg_id == leg_id))
    fin = result.scalar_one_or_none()
    if not fin:
        fin = LegFinance(leg_id=leg_id)
        db.add(fin)
        await db.flush()
    return fin


# ─── FINANCE HOME ────────────────────────────────────────────
@router.get("", response_class=HTMLResponse)
async def finance_home(
    request: Request,
    vessel: Optional[str] = Query(None),
    year: Optional[int] = Query(None),
    user: User = Depends(require_permission("finance", "C")),
    db: AsyncSession = Depends(get_db),
):
    current_year = year or datetime.now().year
    years = list(range(2025, datetime.now().year + 2))
    vessels_result = await db.execute(select(Vessel).where(Vessel.is_active == True).order_by(Vessel.code))
    vessels = vessels_result.scalars().all()

    query = (
        select(Leg)
        .options(selectinload(Leg.vessel), selectinload(Leg.departure_port), selectinload(Leg.arrival_port))
        .where(Leg.year == current_year)
    )
    if vessel:
        v_result = await db.execute(select(Vessel).where(Vessel.code == int(vessel)))
        v = v_result.scalar_one_or_none()
        if v:
            query = query.where(Leg.vessel_id == v.id)

    result = await db.execute(query.order_by(Leg.vessel_id, Leg.sequence))
    legs = result.scalars().all()

    opex_daily = await get_opex_daily(db)
    leg_finances = []
    totals = {
        "rev_f": 0, "rev_a": 0,
        "pax_rev_total": 0, "cargo_rev_total": 0,
        "port_f": 0, "port_a": 0,
        "quay_f": 0, "quay_a": 0,
        "sea_f": 0, "sea_a": 0,
        "ops_f": 0, "ops_a": 0,
        "result_f": 0, "result_a": 0,
    }

    for leg in legs:
        fin_result = await db.execute(select(LegFinance).where(LegFinance.leg_id == leg.id))
        fin = fin_result.scalar_one_or_none()
        order_revenue = await compute_revenue_from_orders(db, leg.id)
        pax_revenue = await compute_pax_revenue_for_leg(db, leg.id)
        defaults = await compute_defaults_for_leg(db, leg)

        rev_f = (fin.revenue_forecast if fin and fin.revenue_forecast else 0) or (order_revenue + pax_revenue)
        rev_a = (fin.revenue_actual if fin else 0) or 0
        port_f = (fin.port_cost_forecast if fin and fin.port_cost_forecast else 0) or defaults["port_f"]
        port_a = fin.port_cost_actual if fin else 0
        quay_f = (fin.quay_cost_forecast if fin and fin.quay_cost_forecast else 0) or defaults["quay_f"]
        quay_a = fin.quay_cost_actual if fin else 0
        sea_f = (fin.sea_cost_forecast if fin and fin.sea_cost_forecast else 0) or defaults["sea_f"]
        sea_a = fin.sea_cost_actual if fin else 0
        ops_f = (fin.ops_cost_forecast if fin and fin.ops_cost_forecast else 0) or defaults["ops_f"]
        ops_a = fin.ops_cost_actual if fin else 0

        total_cost_f = port_f + quay_f + sea_f + ops_f
        total_cost_a = port_a + quay_a + sea_a + ops_a
        result_f = rev_f - total_cost_f
        result_a = rev_a - total_cost_a
        margin_f = round((result_f / rev_f * 100), 1) if rev_f else 0
        margin_a = round((result_a / rev_a * 100), 1) if rev_a else 0
        sea_days = round((leg.estimated_duration_hours or 0) / 24, 1)

        leg_finances.append({
            "leg": leg, "fin": fin, "order_revenue": order_revenue, "pax_revenue": pax_revenue,
            "rev_f": rev_f, "rev_a": rev_a,
            "port_f": port_f, "port_a": port_a,
            "quay_f": quay_f, "quay_a": quay_a,
            "sea_f": sea_f, "sea_a": sea_a, "sea_days": sea_days,
            "ops_f": ops_f, "ops_a": ops_a,
            "total_cost_f": total_cost_f, "total_cost_a": total_cost_a,
            "result_f": result_f, "result_a": result_a,
            "margin_f": margin_f, "margin_a": margin_a,
        })

        for k in ["rev_f", "rev_a", "port_f", "port_a", "quay_f", "quay_a", "sea_f", "sea_a", "ops_f", "ops_a", "result_f", "result_a"]:
            totals[k] += locals()[k]
        totals["pax_rev_total"] += pax_revenue
        totals["cargo_rev_total"] += order_revenue

    totals["total_cost_f"] = totals["port_f"] + totals["quay_f"] + totals["sea_f"] + totals["ops_f"]
    totals["total_cost_a"] = totals["port_a"] + totals["quay_a"] + totals["sea_a"] + totals["ops_a"]
    totals["margin_f"] = round((totals["result_f"] / totals["rev_f"] * 100), 1) if totals["rev_f"] else 0
    totals["margin_a"] = round((totals["result_a"] / totals["rev_a"] * 100), 1) if totals["rev_a"] else 0

    return templates.TemplateResponse("finance/index.html", {
        "request": request, "user": user,
        "vessels": vessels, "selected_vessel": vessel,
        "current_year": current_year, "years": years,
        "leg_finances": leg_finances, "totals": totals,
        "opex_daily": opex_daily,
        "active_module": "finance",
    })


# ─── EDIT LEG FINANCE ────────────────────────────────────────
@router.get("/legs/{leg_id}/edit", response_class=HTMLResponse)
async def finance_edit_form(
    leg_id: int, request: Request,
    user: User = Depends(require_permission("finance", "M")),
    db: AsyncSession = Depends(get_db),
):
    leg_result = await db.execute(
        select(Leg).options(selectinload(Leg.vessel), selectinload(Leg.departure_port), selectinload(Leg.arrival_port))
        .where(Leg.id == leg_id)
    )
    leg = leg_result.scalar_one_or_none()
    if not leg:
        raise HTTPException(status_code=404)

    fin = await get_or_create_finance(db, leg_id)
    order_revenue = await compute_revenue_from_orders(db, leg_id)
    pax_revenue = await compute_pax_revenue_for_leg(db, leg_id)
    defaults = await compute_defaults_for_leg(db, leg)
    opex_daily = await get_opex_daily(db)
    sea_days = round((leg.estimated_duration_hours or 0) / 24, 1)

    return templates.TemplateResponse("finance/edit_form.html", {
        "request": request, "user": user,
        "leg": leg, "fin": fin,
        "order_revenue": order_revenue,
        "pax_revenue": pax_revenue,
        "defaults": defaults,
        "opex_daily": opex_daily,
        "sea_days": sea_days,
    })


@router.post("/legs/{leg_id}/edit", response_class=HTMLResponse)
async def finance_edit_submit(
    leg_id: int, request: Request,
    revenue_forecast: str = Form("0"),
    revenue_actual: str = Form("0"),
    port_cost_forecast: str = Form("0"),
    port_cost_actual: str = Form("0"),
    quay_cost_forecast: str = Form("0"),
    quay_cost_actual: str = Form("0"),
    sea_cost_forecast: str = Form("0"),
    sea_cost_actual: str = Form("0"),
    ops_cost_forecast: str = Form("0"),
    ops_cost_actual: str = Form("0"),
    notes: Optional[str] = Form(None),
    user: User = Depends(require_permission("finance", "M")),
    db: AsyncSession = Depends(get_db),
):
    fin = await get_or_create_finance(db, leg_id)
    fin.revenue_forecast = pf(revenue_forecast)
    fin.revenue_actual = pf(revenue_actual)
    fin.port_cost_forecast = pf(port_cost_forecast)
    fin.port_cost_actual = pf(port_cost_actual)
    fin.quay_cost_forecast = pf(quay_cost_forecast)
    fin.quay_cost_actual = pf(quay_cost_actual)
    fin.sea_cost_forecast = pf(sea_cost_forecast)
    fin.sea_cost_actual = pf(sea_cost_actual)
    fin.ops_cost_forecast = pf(ops_cost_forecast)
    fin.ops_cost_actual = pf(ops_cost_actual)
    fin.notes = notes.strip() if notes else None
    fin.compute()
    await db.flush()
    await log_activity(db, user, "finance", "update", "LegFinance", leg_id, "Modification finances")

    leg_result = await db.execute(select(Leg).options(selectinload(Leg.vessel)).where(Leg.id == leg_id))
    leg = leg_result.scalar_one_or_none()
    url = f"/finance?vessel={leg.vessel.code}&year={leg.year}" if leg else "/finance"
    if request.headers.get("HX-Request"):
        return HTMLResponse(content="", headers={"HX-Redirect": url})
    return RedirectResponse(url=url, status_code=303)


# ─── PORT CONFIG ─────────────────────────────────────────────
@router.get("/ports", response_class=HTMLResponse)
async def port_config_list(
    request: Request,
    user: User = Depends(require_permission("finance", "C")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PortConfig).options(selectinload(PortConfig.port)).order_by(PortConfig.port_locode)
    )
    configs = result.scalars().all()
    return templates.TemplateResponse("finance/port_config.html", {
        "request": request, "user": user,
        "configs": configs, "active_module": "finance",
    })


@router.get("/ports/search", response_class=HTMLResponse)
async def port_search_api(
    q: str = Query(""),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("finance", "C")),
):
    from app.models.port import Port
    if len(q) < 2:
        return HTMLResponse("")
    result = await db.execute(
        select(Port).where((Port.locode.ilike(f"%{q}%")) | (Port.name.ilike(f"%{q}%"))).limit(10)
    )
    ports = result.scalars().all()
    html = ""
    for p in ports:
        html += f'<div class="port-result" onclick="selectPort(\'{p.locode}\',\'{p.name}\')">'
        html += f'<strong>{p.locode}</strong> — {p.name} ({p.country_code})</div>'
    return HTMLResponse(html)


@router.get("/ports/{locode}/edit", response_class=HTMLResponse)
async def port_config_edit_form(
    locode: str, request: Request,
    user: User = Depends(require_permission("finance", "M")),
    db: AsyncSession = Depends(get_db),
):
    from app.models.port import Port
    port_result = await db.execute(select(Port).where(Port.locode == locode))
    port = port_result.scalar_one_or_none()
    if not port:
        raise HTTPException(status_code=404)
    config = await get_port_config(db, locode)
    return templates.TemplateResponse("finance/port_config_form.html", {
        "request": request, "user": user, "port": port, "config": config,
    })


@router.post("/ports/{locode}/edit", response_class=HTMLResponse)
async def port_config_edit_submit(
    locode: str, request: Request,
    accessible: Optional[str] = Form(None),
    port_cost_total: str = Form("0"),
    cost_per_palette: str = Form("0"),
    daily_quay_cost: str = Form("0"),
    notes: Optional[str] = Form(None),
    user: User = Depends(require_permission("finance", "M")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(PortConfig).where(PortConfig.port_locode == locode))
    config = result.scalar_one_or_none()
    if config:
        config.accessible = accessible == "on"
        config.port_cost_total = pf(port_cost_total)
        config.cost_per_palette = pf(cost_per_palette)
        config.daily_quay_cost = pf(daily_quay_cost)
        config.notes = notes.strip() if notes else None
    else:
        config = PortConfig(
            port_locode=locode, accessible=accessible == "on",
            port_cost_total=pf(port_cost_total),
            cost_per_palette=pf(cost_per_palette),
            daily_quay_cost=pf(daily_quay_cost),
            notes=notes.strip() if notes else None,
        )
        db.add(config)
    await db.flush()
    await log_activity(db, user, "finance", "update_port", "PortConfig", None, f"Config port {locode}")
    if request.headers.get("HX-Request"):
        return HTMLResponse(content="", headers={"HX-Redirect": "/finance/ports"})
    return RedirectResponse(url="/finance/ports", status_code=303)


# ─── EXPORT CSV ──────────────────────────────────────────────
@router.get("/export/csv", response_class=StreamingResponse)
async def export_finance_csv(
    user: User = Depends(require_permission("finance", "C")),
    db: AsyncSession = Depends(get_db),
):
    legs_result = await db.execute(
        select(Leg).options(selectinload(Leg.vessel), selectinload(Leg.departure_port), selectinload(Leg.arrival_port))
        .order_by(Leg.year, Leg.vessel_id, Leg.sequence)
    )
    legs = legs_result.scalars().all()
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow([
        "Leg", "Navire", "Année", "Route",
        "CA Prév.", "CA Réel", "Port Prév.", "Port Réel",
        "Escale Prév.", "Escale Réel",
        "OPEX Prév.", "OPEX Réel", "Ops Prév.", "Ops Réel",
        "Résultat Prév.", "Résultat Réel", "Marge Prév. %", "Marge Réelle %",
    ])
    for leg in legs:
        fin_result = await db.execute(select(LegFinance).where(LegFinance.leg_id == leg.id))
        fin = fin_result.scalar_one_or_none()
        defaults = await compute_defaults_for_leg(db, leg)
        order_rev = await compute_revenue_from_orders(db, leg.id)
        pax_rev = await compute_pax_revenue_for_leg(db, leg.id)
        rf = (fin.revenue_forecast if fin and fin.revenue_forecast else 0) or (order_rev + pax_rev)
        ra = fin.revenue_actual if fin else 0
        pf_ = (fin.port_cost_forecast if fin and fin.port_cost_forecast else 0) or defaults["port_f"]
        pa = fin.port_cost_actual if fin else 0
        qf = (fin.quay_cost_forecast if fin and fin.quay_cost_forecast else 0) or defaults["quay_f"]
        qa = fin.quay_cost_actual if fin else 0
        sf = (fin.sea_cost_forecast if fin and fin.sea_cost_forecast else 0) or defaults["sea_f"]
        sa = fin.sea_cost_actual if fin else 0
        of_ = (fin.ops_cost_forecast if fin and fin.ops_cost_forecast else 0) or defaults["ops_f"]
        oa = fin.ops_cost_actual if fin else 0
        res_f = rf - pf_ - qf - sf - of_
        res_a = ra - pa - qa - sa - oa
        mf = round(res_f / rf * 100, 1) if rf else 0
        ma = round(res_a / ra * 100, 1) if ra else 0
        writer.writerow([
            leg.leg_code, leg.vessel.name, leg.year,
            f"{leg.departure_port.locode}→{leg.arrival_port.locode}",
            rf, ra, pf_, pa, qf, qa, sf, sa, of_, oa, res_f, res_a, mf, ma,
        ])
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]), media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=finances_towt.csv"},
    )
