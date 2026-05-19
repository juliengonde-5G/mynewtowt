from fastapi import APIRouter, Request, Depends, Form, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from app.templating import templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case, and_, or_, distinct
from sqlalchemy.orm import selectinload
from typing import Optional
from datetime import datetime
import csv
import io
import math

from app.database import get_db
from app.auth import get_current_user, AuthRequired
from app.permissions import require_permission
from app.models.user import User
from app.models.vessel import Vessel
from app.models.leg import Leg
from app.models.kpi import LegKPI
from app.models.emission_parameter import EmissionParameter
from app.models.co2_variable import Co2Variable, CO2_DEFAULTS
from app.models.order import Order, OrderAssignment
from app.models.operation import EscaleOperation, DockerShift
from app.models.finance import LegFinance, InsuranceContract
from app.models.claim import Claim
from app.models.commercial import Client
from app.utils.activity import log_activity

router = APIRouter(prefix="/kpi", tags=["kpi"])

# ─── EMISSION FACTORS ────────────────────────────────────────
# Default factors (overridable via EmissionParameter table)
DEFAULTS = {
    "conventional_co2_per_ton_nm": 0.0152,   # kg CO2 per ton per NM (conventional cargo)
    "sail_co2_per_ton_nm": 0.00198,           # kg CO2 per ton per NM (TOWT sail cargo)
    "conventional_nox_per_ton_nm": 0.000406,  # kg NOx per ton per NM
    "sail_nox_per_ton_nm": 0.0000528,         # kg NOx per ton per NM
    "conventional_sox_per_ton_nm": 0.0000812,  # kg SOx per ton per NM
    "sail_sox_per_ton_nm": 0.00001056,         # kg SOx per ton per NM
    "co2_reduction_pct": 87,                   # % reduction vs conventional
    # Equivalences
    "co2_per_flight_paris_nyc": 525,           # tonnes CO2 for 1 Paris-NYC flight (plane, ~300 pax)
    "co2_per_container_asia_eu": 2.5,          # tonnes CO2 for 1 container Asia-Europe conventional
}


async def get_co2_variables(db: AsyncSession) -> dict:
    """Get current CO2 decarbonation variables from DB, fallback to defaults."""
    result = await db.execute(
        select(Co2Variable).where(Co2Variable.is_current == True)
    )
    stored = {v.variable_name: v.variable_value for v in result.scalars().all()}
    return {k: stored.get(k, info["value"]) for k, info in CO2_DEFAULTS.items()}


def compute_decarbonation(cargo_tons: float, distance_nm: float, co2_vars: dict) -> dict:
    """Compute decarbonation for given cargo and distance."""
    towt_ef = co2_vars.get("towt_co2_ef", 1.5)
    conv_ef = co2_vars.get("conventional_co2_ef", 13.7)
    capacity = co2_vars.get("sailing_cargo_capacity", 1100)
    nm_to_km = co2_vars.get("nm_to_km", 1.852)

    if not cargo_tons or not distance_nm:
        return {"decarb_g": 0, "decarb_kg": 0, "decarb_t": 0, "fill_rate_pct": 0}

    fill_rate = min(cargo_tons / capacity, 1.0) if capacity > 0 else 0
    decarb_g = (conv_ef - towt_ef) * fill_rate * capacity * distance_nm * nm_to_km
    decarb_kg = decarb_g / 1000
    decarb_t = decarb_kg / 1000

    return {
        "decarb_g": round(decarb_g, 1),
        "decarb_kg": round(decarb_kg, 2),
        "decarb_t": round(decarb_t, 3),
        "fill_rate_pct": round(fill_rate * 100, 1),
    }


async def get_emission_params(db: AsyncSession) -> dict:
    """Get emission parameters from DB, fallback to defaults."""
    result = await db.execute(select(EmissionParameter))
    params = {p.parameter_name: p.parameter_value for p in result.scalars().all()}
    merged = {**DEFAULTS, **{k: float(v) for k, v in params.items() if v}}
    return merged


def compute_leg_kpi(leg, cargo_tons: float, params: dict) -> dict:
    """Compute all KPIs for a single leg."""
    distance = leg.computed_distance or (leg.distance_nm * (leg.elongation_coeff or 1.25) if leg.distance_nm else 0)
    if not distance or not cargo_tons:
        return {
            "co2_conventional_kg": 0, "co2_sail_kg": 0, "co2_avoided_kg": 0,
            "nox_conventional_kg": 0, "nox_sail_kg": 0, "nox_avoided_kg": 0,
            "sox_conventional_kg": 0, "sox_sail_kg": 0, "sox_avoided_kg": 0,
            "co2_per_ton_kg": 0, "occupation_pct": 0, "distance_nm": distance,
            "equiv_flights_paris_nyc": 0, "equiv_containers_asia_eu": 0,
        }

    co2_conv = cargo_tons * distance * params["conventional_co2_per_ton_nm"]
    co2_sail = cargo_tons * distance * params["sail_co2_per_ton_nm"]
    co2_avoided = co2_conv - co2_sail
    nox_conv = cargo_tons * distance * params["conventional_nox_per_ton_nm"]
    nox_sail = cargo_tons * distance * params["sail_nox_per_ton_nm"]
    nox_avoided = nox_conv - nox_sail
    sox_conv = cargo_tons * distance * params["conventional_sox_per_ton_nm"]
    sox_sail = cargo_tons * distance * params["sail_sox_per_ton_nm"]
    sox_avoided = sox_conv - sox_sail
    co2_per_ton = co2_sail / cargo_tons if cargo_tons > 0 else 0
    vessel_capacity = leg.vessel.dwt if leg.vessel and leg.vessel.dwt else 1000
    occupation = min(100, (cargo_tons / vessel_capacity) * 100)
    co2_avoided_tons = co2_avoided / 1000
    equiv_flights = co2_avoided_tons / params["co2_per_flight_paris_nyc"] if params["co2_per_flight_paris_nyc"] > 0 else 0
    equiv_containers = co2_avoided_tons / params["co2_per_container_asia_eu"] if params["co2_per_container_asia_eu"] > 0 else 0

    return {
        "co2_conventional_kg": round(co2_conv, 1),
        "co2_sail_kg": round(co2_sail, 1),
        "co2_avoided_kg": round(co2_avoided, 1),
        "nox_conventional_kg": round(nox_conv, 2),
        "nox_sail_kg": round(nox_sail, 2),
        "nox_avoided_kg": round(nox_avoided, 2),
        "sox_conventional_kg": round(sox_conv, 2),
        "sox_sail_kg": round(sox_sail, 2),
        "sox_avoided_kg": round(sox_avoided, 2),
        "co2_per_ton_kg": round(co2_per_ton, 3),
        "occupation_pct": round(occupation, 1),
        "distance_nm": round(distance, 1),
        "equiv_flights_paris_nyc": round(equiv_flights, 2),
        "equiv_containers_asia_eu": round(equiv_containers, 1),
    }


# ─── KPI DASHBOARD ───────────────────────────────────────────
@router.get("", response_class=HTMLResponse)
async def kpi_dashboard(
    request: Request,
    vessel: Optional[int] = Query(None),
    year: Optional[int] = Query(None),
    route: Optional[str] = Query(None),
    leg_id: Optional[int] = Query(None),
    tab: Optional[str] = Query("operations"),
    user: User = Depends(require_permission("kpi", "C")),
    db: AsyncSession = Depends(get_db),
):
    current_year = year or datetime.now().year
    years = list(range(2025, datetime.now().year + 2))

    vessels_result = await db.execute(select(Vessel).where(Vessel.is_active == True).order_by(Vessel.code))
    vessels = vessels_result.scalars().all()

    params = await get_emission_params(db)
    co2_vars = await get_co2_variables(db)

    # ── Get all legs (optionally filtered) ──
    query = (
        select(Leg)
        .options(selectinload(Leg.vessel), selectinload(Leg.departure_port), selectinload(Leg.arrival_port))
        .where(Leg.year == current_year)
    )
    vessel_obj = None
    if vessel:
        v_result = await db.execute(select(Vessel).where(Vessel.code == vessel))
        vessel_obj = v_result.scalar_one_or_none()
        if vessel_obj:
            query = query.where(Leg.vessel_id == vessel_obj.id)

    if route:
        parts = route.split("-")
        if len(parts) == 2:
            query = query.where(Leg.departure_port_locode == parts[0], Leg.arrival_port_locode == parts[1])

    if leg_id:
        query = query.where(Leg.id == leg_id)

    result = await db.execute(query.order_by(Leg.vessel_id, Leg.sequence))
    legs = result.scalars().all()
    leg_ids = [l.id for l in legs]

    # ── Build available routes for filter dropdown ──
    all_legs_q = (
        select(Leg)
        .options(selectinload(Leg.departure_port), selectinload(Leg.arrival_port))
        .where(Leg.year == current_year)
    )
    if vessel_obj:
        all_legs_q = all_legs_q.where(Leg.vessel_id == vessel_obj.id)
    all_legs_result = await db.execute(all_legs_q.order_by(Leg.sequence))
    all_legs_for_routes = all_legs_result.scalars().all()

    routes_set = {}
    legs_for_filter = []
    for l in all_legs_for_routes:
        route_key = f"{l.departure_port_locode}-{l.arrival_port_locode}"
        if route_key not in routes_set:
            routes_set[route_key] = {
                "key": route_key,
                "label": f"{l.departure_port.name} → {l.arrival_port.name}",
                "dep": l.departure_port_locode,
                "arr": l.arrival_port_locode,
            }
        legs_for_filter.append({"id": l.id, "code": l.leg_code})
    available_routes = list(routes_set.values())

    # ── KPI data (cargo tons) ──
    kpi_data = {}
    kpi_result = await db.execute(select(LegKPI))
    for k in kpi_result.scalars().all():
        kpi_data[k.leg_id] = k

    # ══════════════════════════════════════════════════════════
    # 1. OPERATIONS KPIs
    # ══════════════════════════════════════════════════════════
    ops_data = {}

    # Operations by leg
    if leg_ids:
        ops_result = await db.execute(
            select(EscaleOperation).where(EscaleOperation.leg_id.in_(leg_ids))
        )
        all_ops = ops_result.scalars().all()

        shifts_result = await db.execute(
            select(DockerShift).where(DockerShift.leg_id.in_(leg_ids))
        )
        all_shifts = shifts_result.scalars().all()
    else:
        all_ops = []
        all_shifts = []

    # Total operation duration (actual hours)
    total_ops_duration = sum(o.actual_duration_hours or 0 for o in all_ops)
    total_ops_planned_duration = sum(o.planned_duration_hours or 0 for o in all_ops)
    ops_count = len(all_ops)

    # Docker shift productivity
    total_actual_palettes = sum(s.actual_palettes or 0 for s in all_shifts)
    total_shift_hours = 0
    for s in all_shifts:
        if s.actual_start and s.actual_end:
            total_shift_hours += (s.actual_end - s.actual_start).total_seconds() / 3600

    productivity_palettes_h = round(total_actual_palettes / total_shift_hours, 1) if total_shift_hours > 0 else 0

    # Claims per escale
    if leg_ids:
        claims_result = await db.execute(
            select(Claim).where(Claim.leg_id.in_(leg_ids))
        )
        all_claims = claims_result.scalars().all()
    else:
        all_claims = []

    claims_total = len(all_claims)
    claims_per_escale = round(claims_total / len(legs), 2) if legs else 0

    # LOP count (letter of protest = claims with context "loading" or "unloading" that are cargo type)
    lop_count = sum(1 for c in all_claims if c.claim_type == "cargo" and c.context in ("loading", "unloading"))

    ops_data = {
        "total_duration_h": round(total_ops_duration, 1),
        "planned_duration_h": round(total_ops_planned_duration, 1),
        "ops_count": ops_count,
        "productivity_pal_h": productivity_palettes_h,
        "total_palettes": total_actual_palettes,
        "total_shift_hours": round(total_shift_hours, 1),
        "shifts_count": len(all_shifts),
        "claims_total": claims_total,
        "claims_per_escale": claims_per_escale,
        "claims_open": sum(1 for c in all_claims if c.status in ("open", "declared", "instruction")),
        "claims_closed": sum(1 for c in all_claims if c.status in ("accepted", "refused", "closed")),
        "claims_cargo": sum(1 for c in all_claims if c.claim_type == "cargo"),
        "claims_crew": sum(1 for c in all_claims if c.claim_type == "crew"),
        "claims_hull": sum(1 for c in all_claims if c.claim_type == "hull"),
        "lop_count": lop_count,
    }

    # ══════════════════════════════════════════════════════════
    # 2. COMMERCE KPIs
    # ══════════════════════════════════════════════════════════
    if leg_ids:
        assignments_result = await db.execute(
            select(OrderAssignment)
            .options(selectinload(OrderAssignment.order).selectinload(Order.rate_grid))
            .where(OrderAssignment.leg_id.in_(leg_ids))
        )
        all_assignments = assignments_result.scalars().all()
    else:
        all_assignments = []

    orders_on_legs = [a.order for a in all_assignments if a.order]

    # Volume de chargement (total palettes)
    total_palettes_loaded = sum(o.quantity_palettes or 0 for o in orders_on_legs)
    total_weight_loaded = sum(o.total_weight or 0 for o in orders_on_legs)

    # Taux de remplissage (avg occupation across legs)
    fill_rates = []
    for leg in legs:
        leg_assignments = [a for a in all_assignments if a.leg_id == leg.id]
        leg_palettes = sum(a.order.quantity_palettes or 0 for a in leg_assignments if a.order)
        capacity = leg.vessel.max_palettes if leg.vessel and leg.vessel.max_palettes else 850
        if capacity > 0:
            fill_rates.append(min(100, leg_palettes / capacity * 100))

    avg_fill_rate = round(sum(fill_rates) / len(fill_rates), 1) if fill_rates else 0

    # Prix moyen par palette
    total_revenue_orders = sum(o.total_price or 0 for o in orders_on_legs)
    avg_price_palette = round(total_revenue_orders / total_palettes_loaded, 2) if total_palettes_loaded > 0 else 0

    # Histogramme par typologie de chargeurs (shipper vs freight forwarder)
    # Group orders by client type via rate_grid -> client
    client_type_volumes = {"shipper": 0, "freight_forwarder": 0, "unknown": 0}
    for o in orders_on_legs:
        if o.rate_grid and o.rate_grid.client:
            ct = o.rate_grid.client.client_type or "unknown"
            client_type_volumes[ct] = client_type_volumes.get(ct, 0) + (o.quantity_palettes or 0)
        else:
            client_type_volumes["unknown"] += (o.quantity_palettes or 0)

    # Par format palette (EPAL, USPAL, PORTPAL)
    cargo_type_volumes = {}
    for o in orders_on_legs:
        fmt = o.palette_format or "EPAL"
        cargo_type_volumes[fmt] = cargo_type_volumes.get(fmt, 0) + (o.quantity_palettes or 0)

    # Par groupe de prix unitaire
    price_groups = {"< 100 €": 0, "100–200 €": 0, "200–300 €": 0, "300–500 €": 0, "> 500 €": 0}
    for o in orders_on_legs:
        up = o.unit_price or 0
        if up < 100:
            price_groups["< 100 €"] += (o.quantity_palettes or 0)
        elif up < 200:
            price_groups["100–200 €"] += (o.quantity_palettes or 0)
        elif up < 300:
            price_groups["200–300 €"] += (o.quantity_palettes or 0)
        elif up < 500:
            price_groups["300–500 €"] += (o.quantity_palettes or 0)
        else:
            price_groups["> 500 €"] += (o.quantity_palettes or 0)

    commerce_data = {
        "total_palettes": total_palettes_loaded,
        "total_weight": round(total_weight_loaded, 1),
        "avg_fill_rate": avg_fill_rate,
        "fill_rates_by_leg": fill_rates,
        "avg_price_palette": avg_price_palette,
        "total_revenue": round(total_revenue_orders, 2),
        "orders_count": len(orders_on_legs),
        "client_type_volumes": client_type_volumes,
        "cargo_type_volumes": cargo_type_volumes,
        "price_groups": price_groups,
    }

    # ══════════════════════════════════════════════════════════
    # 3. ENVIRONNEMENT KPIs
    # ══════════════════════════════════════════════════════════
    leg_kpis = []
    env_totals = {
        "co2_avoided_kg": 0, "nox_avoided_kg": 0, "sox_avoided_kg": 0,
        "distance_nm": 0, "cargo_tons": 0, "co2_sail_kg": 0,
        "equiv_flights": 0, "equiv_containers": 0, "occupation_sum": 0,
        "leg_count": 0, "decarb_t": 0,
    }

    for leg in legs:
        stored = kpi_data.get(leg.id)
        cargo_tons = stored.cargo_tons if stored else 0
        kpi = compute_leg_kpi(leg, cargo_tons, params)
        decarb = compute_decarbonation(cargo_tons, kpi["distance_nm"], co2_vars)
        kpi["leg"] = leg
        kpi["cargo_tons"] = cargo_tons
        kpi["decarb_t"] = decarb["decarb_t"]
        kpi["decarb_kg"] = decarb["decarb_kg"]
        kpi["fill_rate_pct"] = decarb["fill_rate_pct"]
        leg_kpis.append(kpi)

        env_totals["co2_avoided_kg"] += kpi["co2_avoided_kg"]
        env_totals["nox_avoided_kg"] += kpi["nox_avoided_kg"]
        env_totals["sox_avoided_kg"] += kpi["sox_avoided_kg"]
        env_totals["distance_nm"] += kpi["distance_nm"]
        env_totals["cargo_tons"] += cargo_tons
        env_totals["co2_sail_kg"] += kpi["co2_sail_kg"]
        env_totals["equiv_flights"] += kpi["equiv_flights_paris_nyc"]
        env_totals["equiv_containers"] += kpi["equiv_containers_asia_eu"]
        env_totals["occupation_sum"] += kpi["occupation_pct"]
        env_totals["leg_count"] += 1
        env_totals["decarb_t"] += decarb["decarb_t"]

    env_totals["occupation_avg"] = round(env_totals["occupation_sum"] / env_totals["leg_count"], 1) if env_totals["leg_count"] > 0 else 0
    env_totals["co2_per_ton_avg"] = round(env_totals["co2_sail_kg"] / env_totals["cargo_tons"], 3) if env_totals["cargo_tons"] > 0 else 0

    env_data = {
        "co2_avoided_t": round(env_totals["co2_avoided_kg"] / 1000, 2),
        "co2_avoided_kg": round(env_totals["co2_avoided_kg"], 1),
        "nox_avoided_kg": round(env_totals["nox_avoided_kg"], 1),
        "sox_avoided_kg": round(env_totals["sox_avoided_kg"], 1),
        "distance_nm": round(env_totals["distance_nm"], 0),
        "cargo_tons": round(env_totals["cargo_tons"], 0),
        "decarb_t": round(env_totals["decarb_t"], 2),
        "equiv_flights": round(env_totals["equiv_flights"], 1),
        "equiv_containers": round(env_totals["equiv_containers"], 0),
        "co2_per_ton_avg": env_totals["co2_per_ton_avg"],
        "occupation_avg": env_totals["occupation_avg"],
        "leg_count": env_totals["leg_count"],
        "conv_co2_per_ton": round(params["conventional_co2_per_ton_nm"] * 4000, 1),
    }

    # ══════════════════════════════════════════════════════════
    # 4. FINANCES KPIs
    # ══════════════════════════════════════════════════════════
    if leg_ids:
        fin_result = await db.execute(
            select(LegFinance).where(LegFinance.leg_id.in_(leg_ids))
        )
        all_finances = fin_result.scalars().all()
    else:
        all_finances = []

    total_revenue_actual = sum(f.revenue_actual or 0 for f in all_finances)
    total_revenue_forecast = sum(f.revenue_forecast or 0 for f in all_finances)
    total_sea_cost = sum(f.sea_cost_actual or 0 for f in all_finances)
    total_port_cost = sum(f.port_cost_actual or 0 for f in all_finances)
    total_quay_cost = sum(f.quay_cost_actual or 0 for f in all_finances)
    total_ops_cost = sum(f.ops_cost_actual or 0 for f in all_finances)
    total_claims_cost = sum(f.claims_cost or 0 for f in all_finances)
    total_result_actual = sum(f.result_actual or 0 for f in all_finances)
    total_result_forecast = sum(f.result_forecast or 0 for f in all_finances)

    total_costs = total_sea_cost + total_port_cost + total_quay_cost + total_ops_cost + total_claims_cost
    margin_rate = round(total_result_actual / total_revenue_actual * 100, 1) if total_revenue_actual > 0 else 0

    # Insurance exposure
    ins_result = await db.execute(select(InsuranceContract).where(InsuranceContract.is_active == True))
    insurance_contracts = ins_result.scalars().all()
    total_provisions = sum(float(c.provision_amount or 0) for c in all_claims)
    total_indemnities = sum(float(c.indemnity_amount or 0) for c in all_claims)
    total_franchises = sum(float(c.franchise_amount or 0) for c in all_claims)

    cost_groups = {
        "Coûts mer": total_sea_cost,
        "Coûts portuaires": total_port_cost,
        "Coûts quai": total_quay_cost,
        "Coûts opérations": total_ops_cost,
        "Sinistres": total_claims_cost,
    }

    finance_data = {
        "revenue_actual": round(total_revenue_actual, 2),
        "revenue_forecast": round(total_revenue_forecast, 2),
        "total_costs": round(total_costs, 2),
        "result_actual": round(total_result_actual, 2),
        "result_forecast": round(total_result_forecast, 2),
        "margin_rate": margin_rate,
        "cost_groups": cost_groups,
        "total_provisions": round(total_provisions, 2),
        "total_indemnities": round(total_indemnities, 2),
        "total_franchises": round(total_franchises, 2),
        "insurance_contracts": insurance_contracts,
        "legs_with_finance": len(all_finances),
    }

    # ══════════════════════════════════════════════════════════
    # 5. EXPLOITATION KPIs
    # ══════════════════════════════════════════════════════════

    # Taux d'activité: % of days with vessel in use (legs in progress/completed)
    completed_legs = [l for l in legs if l.status in ("completed", "in_progress")]
    total_nav_days = 0
    total_port_days = 0
    planning_ecarts = []  # Ecart par rapport au planning

    for leg in legs:
        # Navigation duration
        if leg.atd and leg.ata:
            nav_hours = (leg.ata - leg.atd).total_seconds() / 3600
            total_nav_days += nav_hours / 24
        elif leg.estimated_duration_hours:
            total_nav_days += (leg.estimated_duration_hours or 0) / 24

        # Port stay
        total_port_days += leg.port_stay_days or 0

        # Ecart planning: difference between planned ETD and actual ATD
        if leg.etd and leg.atd:
            ecart_hours = (leg.atd - leg.etd).total_seconds() / 3600
            planning_ecarts.append({
                "leg_code": leg.leg_code,
                "ecart_hours": round(ecart_hours, 1),
                "ecart_days": round(ecart_hours / 24, 1),
            })

    # Days in year so far
    year_start = datetime(current_year, 1, 1)
    year_end = datetime(current_year, 12, 31)
    now = datetime.now()
    days_elapsed = (min(now, year_end) - year_start).days + 1 if current_year <= now.year else 365
    total_activity_days = total_nav_days + total_port_days

    # Nb of active vessels
    active_vessel_count = 1
    if not vessel_obj:
        vessel_ids_in_legs = set(l.vessel_id for l in legs)
        active_vessel_count = max(len(vessel_ids_in_legs), 1)

    taux_activite = round(total_activity_days / (days_elapsed * active_vessel_count) * 100, 1) if days_elapsed > 0 else 0

    # Vitesse d'exploitation moyenne
    speeds = []
    for leg in legs:
        if leg.atd and leg.ata and leg.computed_distance:
            nav_hours = (leg.ata - leg.atd).total_seconds() / 3600
            if nav_hours > 0:
                speeds.append(leg.computed_distance / nav_hours)
        elif leg.speed_knots:
            speeds.append(leg.speed_knots)

    avg_speed = round(sum(speeds) / len(speeds), 1) if speeds else 0

    # Durée moyenne de navigation par route
    route_nav_durations = {}
    for leg in legs:
        route_key = f"{leg.departure_port_locode}-{leg.arrival_port_locode}"
        duration_h = None
        if leg.atd and leg.ata:
            duration_h = (leg.ata - leg.atd).total_seconds() / 3600
        elif leg.estimated_duration_hours:
            duration_h = leg.estimated_duration_hours
        if duration_h is not None:
            if route_key not in route_nav_durations:
                dep_name = leg.departure_port.name if leg.departure_port else leg.departure_port_locode
                arr_name = leg.arrival_port.name if leg.arrival_port else leg.arrival_port_locode
                route_nav_durations[route_key] = {"label": f"{dep_name} → {arr_name}", "durations": []}
            route_nav_durations[route_key]["durations"].append(duration_h)

    route_avg_durations = []
    for rk, rd in route_nav_durations.items():
        avg_d = sum(rd["durations"]) / len(rd["durations"])
        route_avg_durations.append({
            "route": rd["label"],
            "avg_hours": round(avg_d, 1),
            "avg_days": round(avg_d / 24, 1),
            "count": len(rd["durations"]),
        })

    exploitation_data = {
        "taux_activite": min(taux_activite, 100),
        "total_nav_days": round(total_nav_days, 1),
        "total_port_days": round(total_port_days, 1),
        "total_activity_days": round(total_activity_days, 1),
        "days_elapsed": days_elapsed,
        "planning_ecarts": planning_ecarts,
        "avg_ecart_hours": round(sum(abs(e["ecart_hours"]) for e in planning_ecarts) / len(planning_ecarts), 1) if planning_ecarts else 0,
        "avg_speed_knots": avg_speed,
        "route_avg_durations": route_avg_durations,
        "completed_legs": len(completed_legs),
        "total_legs": len(legs),
    }

    # ── Claims statistics for KPI dashboard ──
    claims_query = select(Claim).join(Leg, Claim.leg_id == Leg.id).where(Leg.year == current_year)
    if vessel_obj:
        claims_query = claims_query.where(Claim.vessel_id == vessel_obj.id)
    claims_result = await db.execute(claims_query)
    all_claims = claims_result.scalars().all()
    claims_stats = {
        "total": len(all_claims),
        "open": sum(1 for c in all_claims if c.status in ("open", "declared", "instruction")),
        "closed": sum(1 for c in all_claims if c.status in ("accepted", "refused", "closed")),
        "cargo": sum(1 for c in all_claims if c.claim_type == "cargo"),
        "crew": sum(1 for c in all_claims if c.claim_type == "crew"),
        "hull": sum(1 for c in all_claims if c.claim_type == "hull"),
        "total_provision": sum(float(c.provision_amount or 0) for c in all_claims),
        "total_indemnity": sum(float(c.indemnity_amount or 0) for c in all_claims),
    }
    claims_per_leg = round(claims_stats["total"] / env_totals["leg_count"], 2) if env_totals["leg_count"] > 0 else 0

    return templates.TemplateResponse("kpi/index.html", {
        "request": request,
        "user": user,
        "vessels": vessels,
        "selected_vessel": vessel,
        "current_year": current_year,
        "years": years,
        "active_tab": tab,
        "selected_route": route,
        "selected_leg_id": leg_id,
        "available_routes": available_routes,
        "legs_for_filter": legs_for_filter,
        "legs": legs,
        "leg_kpis": leg_kpis,
        "ops_data": ops_data,
        "commerce_data": commerce_data,
        "env_data": env_data,
        "finance_data": finance_data,
        "exploitation_data": exploitation_data,
        "params": params,
        "co2_vars": co2_vars,
        "active_module": "kpi",
    })


# ─── UPDATE CARGO TONS (inline edit) ─────────────────────────
@router.post("/legs/{leg_id}/cargo", response_class=HTMLResponse)
async def update_cargo(
    leg_id: int,
    request: Request,
    cargo_tons: str = Form(...),
    user: User = Depends(require_permission("kpi", "M")),
    db: AsyncSession = Depends(get_db),
):
    _tons = 0
    try:
        _tons = float(cargo_tons) if cargo_tons.strip() else 0
    except ValueError:
        _tons = 0

    result = await db.execute(select(LegKPI).where(LegKPI.leg_id == leg_id))
    kpi = result.scalar_one_or_none()
    if kpi:
        kpi.cargo_tons = _tons
    else:
        kpi = LegKPI(leg_id=leg_id, cargo_tons=_tons)
        db.add(kpi)

    await db.flush()
    await log_activity(db, user, "kpi", "update_cargo", "LegKPI", leg_id, f"Tonnage cargo → {_tons}t")

    leg_result = await db.execute(select(Leg).options(selectinload(Leg.vessel)).where(Leg.id == leg_id))
    leg = leg_result.scalar_one_or_none()
    year = leg.year if leg else datetime.now().year
    vessel_code = leg.vessel.code if leg and leg.vessel else ""

    url = f"/kpi?year={year}&tab=environnement" + (f"&vessel={vessel_code}" if vessel_code else "")
    if request.headers.get("HX-Request"):
        return HTMLResponse(content="", headers={"HX-Redirect": url})
    return RedirectResponse(url=url, status_code=303)


# ─── EXPORT KPI CSV ──────────────────────────────────────────
@router.get("/export/csv", response_class=StreamingResponse)
async def export_kpi_csv(
    user: User = Depends(require_permission("kpi", "C")),
    db: AsyncSession = Depends(get_db),
):
    params = await get_emission_params(db)
    co2_vars = await get_co2_variables(db)

    legs_result = await db.execute(
        select(Leg)
        .options(selectinload(Leg.vessel), selectinload(Leg.departure_port), selectinload(Leg.arrival_port))
        .order_by(Leg.year, Leg.vessel_id, Leg.sequence)
    )
    legs = legs_result.scalars().all()

    kpi_result = await db.execute(select(LegKPI))
    kpi_data = {k.leg_id: k for k in kpi_result.scalars().all()}

    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow([
        "Leg", "Navire", "Année", "Départ", "Arrivée", "Distance (NM)",
        "Tonnes transportées", "Occupation (%)",
        "CO2 conventionnel (kg)", "CO2 voile (kg)", "CO2 évité (kg)",
        "NOx évité (kg)", "SOx évité (kg)",
        "CO2/tonne (kg)", "Equiv. vols Paris-NYC", "Equiv. containers Asie-EU",
        "Décarbonation (t CO2)"
    ])

    for leg in legs:
        stored = kpi_data.get(leg.id)
        cargo = stored.cargo_tons if stored else 0
        kpi = compute_leg_kpi(leg, cargo, params)
        decarb = compute_decarbonation(cargo, kpi["distance_nm"], co2_vars)
        writer.writerow([
            leg.leg_code, leg.vessel.name, leg.year,
            leg.departure_port.locode, leg.arrival_port.locode,
            kpi["distance_nm"], cargo, kpi["occupation_pct"],
            kpi["co2_conventional_kg"], kpi["co2_sail_kg"], kpi["co2_avoided_kg"],
            kpi["nox_avoided_kg"], kpi["sox_avoided_kg"],
            kpi["co2_per_ton_kg"], kpi["equiv_flights_paris_nyc"], kpi["equiv_containers_asia_eu"],
            decarb["decarb_t"],
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=kpi_towt.csv"},
    )


# ─── SYNC CARGO TONS FROM ORDERS ─────────────────────────────
@router.post("/sync-cargo", response_class=HTMLResponse)
async def sync_cargo_from_orders(
    request: Request,
    year: Optional[int] = Form(None),
    vessel: Optional[int] = Form(None),
    user: User = Depends(require_permission("kpi", "M")),
    db: AsyncSession = Depends(get_db),
):
    """Auto-calculate cargo_tons for each leg from confirmed OrderAssignment total_weight."""
    current_year = year or datetime.now().year
    query = select(Leg).where(Leg.year == current_year)
    if vessel:
        v_result = await db.execute(select(Vessel).where(Vessel.code == vessel))
        v_obj = v_result.scalar_one_or_none()
        if v_obj:
            query = query.where(Leg.vessel_id == v_obj.id)

    legs_result = await db.execute(query)
    legs = legs_result.scalars().all()
    leg_ids = [l.id for l in legs]

    if not leg_ids:
        url = f"/kpi?year={current_year}&tab=environnement"
        if request.headers.get("HX-Request"):
            return HTMLResponse(content="", headers={"HX-Redirect": url})
        return RedirectResponse(url=url, status_code=303)

    # Sum total_weight from orders via assignments
    assignments_result = await db.execute(
        select(OrderAssignment)
        .options(selectinload(OrderAssignment.order))
        .where(OrderAssignment.leg_id.in_(leg_ids))
    )
    all_assignments = assignments_result.scalars().all()

    # Group by leg
    weight_by_leg = {}
    for a in all_assignments:
        if a.order and a.order.total_weight:
            weight_by_leg[a.leg_id] = weight_by_leg.get(a.leg_id, 0) + a.order.total_weight

    # Load existing KPI records
    kpi_result = await db.execute(select(LegKPI).where(LegKPI.leg_id.in_(leg_ids)))
    kpi_map = {k.leg_id: k for k in kpi_result.scalars().all()}

    synced = 0
    for lid in leg_ids:
        tons = round(weight_by_leg.get(lid, 0), 2)
        if tons > 0:
            if lid in kpi_map:
                kpi_map[lid].cargo_tons = tons
            else:
                db.add(LegKPI(leg_id=lid, cargo_tons=tons))
            synced += 1

    await db.flush()
    await log_activity(db, user, "kpi", "sync_cargo", "LegKPI", 0,
                        f"Sync tonnage depuis commandes: {synced} legs, année {current_year}")

    url = f"/kpi?year={current_year}&tab=environnement" + (f"&vessel={vessel}" if vessel else "")
    if request.headers.get("HX-Request"):
        return HTMLResponse(content="", headers={"HX-Redirect": url})
    return RedirectResponse(url=url, status_code=303)


# ─── DECARBONATION CERTIFICATE PDF ──────────────────────────
@router.get("/certificate", response_class=StreamingResponse)
async def decarbonation_certificate(
    client_name: str = Query(...),
    year: Optional[int] = Query(None),
    user: User = Depends(require_permission("kpi", "C")),
    db: AsyncSession = Depends(get_db),
):
    """Generate a PDF decarbonation certificate for a specific client."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    current_year = year or datetime.now().year
    params = await get_emission_params(db)
    co2_vars = await get_co2_variables(db)

    # Find orders for this client (via client_name on Order or via Client table)
    orders_q = (
        select(OrderAssignment)
        .options(
            selectinload(OrderAssignment.order).selectinload(Order.rate_grid),
            selectinload(OrderAssignment.leg).selectinload(Leg.vessel),
            selectinload(OrderAssignment.leg).selectinload(Leg.departure_port),
            selectinload(OrderAssignment.leg).selectinload(Leg.arrival_port),
        )
        .join(OrderAssignment.order)
        .join(OrderAssignment.leg)
        .where(Leg.year == current_year)
    )

    # Try matching by Order.client_name or Client.company_name
    from sqlalchemy import or_
    from app.models.commercial import RateGrid
    orders_q = orders_q.outerjoin(Order.rate_grid).outerjoin(RateGrid.client).where(
        or_(
            Order.client_name.ilike(f"%{client_name}%"),
            Client.company_name.ilike(f"%{client_name}%"),
        )
    )

    result = await db.execute(orders_q)
    assignments = result.scalars().all()

    if not assignments:
        raise HTTPException(404, detail=f"Aucune commande trouvée pour '{client_name}' en {current_year}")

    # Compute per-leg CO2 data
    cert_legs = []
    total_co2_avoided = 0
    total_cargo = 0
    total_distance = 0

    leg_seen = {}
    for a in assignments:
        if not a.leg or a.leg.id in leg_seen:
            continue
        leg_seen[a.leg.id] = True
        cargo_tons = a.order.total_weight or 0
        kpi = compute_leg_kpi(a.leg, cargo_tons, params)
        decarb = compute_decarbonation(cargo_tons, kpi["distance_nm"], co2_vars)
        cert_legs.append({
            "leg_code": a.leg.leg_code,
            "route": f"{a.leg.departure_port.name if a.leg.departure_port else '?'} → {a.leg.arrival_port.name if a.leg.arrival_port else '?'}",
            "vessel": a.leg.vessel.name if a.leg.vessel else "?",
            "cargo_tons": round(cargo_tons, 1),
            "distance_nm": kpi["distance_nm"],
            "co2_avoided_kg": kpi["co2_avoided_kg"],
            "decarb_t": decarb["decarb_t"],
        })
        total_co2_avoided += kpi["co2_avoided_kg"]
        total_cargo += cargo_tons
        total_distance += kpi["distance_nm"]

    # Generate PDF
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=20*mm, rightMargin=20*mm, topMargin=25*mm, bottomMargin=20*mm)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle("CertTitle", parent=styles["Title"], fontSize=20,
                                  textColor=colors.HexColor("#0a6b7a"), spaceAfter=6)
    subtitle_style = ParagraphStyle("CertSub", parent=styles["Normal"], fontSize=12,
                                     textColor=colors.HexColor("#666"), spaceAfter=20)
    body_style = ParagraphStyle("CertBody", parent=styles["Normal"], fontSize=11, leading=16)
    bold_style = ParagraphStyle("CertBold", parent=body_style, fontName="Helvetica-Bold")

    elements = []
    elements.append(Paragraph("CERTIFICAT DE DÉCARBONATION", title_style))
    elements.append(Paragraph("DECARBONATION CERTIFICATE", subtitle_style))
    elements.append(Spacer(1, 10))

    elements.append(Paragraph(f"<b>Client :</b> {client_name}", body_style))
    elements.append(Paragraph(f"<b>Année :</b> {current_year}", body_style))
    elements.append(Paragraph(f"<b>Date d'émission :</b> {datetime.now().strftime('%d/%m/%Y')}", body_style))
    elements.append(Spacer(1, 15))

    elements.append(Paragraph(
        "TOWT (Transport à la Voile) certifie que le client ci-dessus a contribué à la décarbonation "
        "du transport maritime en utilisant nos voiliers-cargos pour les traversées suivantes :",
        body_style
    ))
    elements.append(Spacer(1, 12))

    # Detail table
    table_data = [["Leg", "Route", "Navire", "Cargo (t)", "Distance (NM)", "CO₂ évité (kg)"]]
    for cl in cert_legs:
        table_data.append([
            cl["leg_code"], cl["route"], cl["vessel"],
            f"{cl['cargo_tons']:.1f}", f"{cl['distance_nm']:.0f}", f"{cl['co2_avoided_kg']:.1f}"
        ])
    table_data.append(["TOTAL", "", "", f"{total_cargo:.1f}", f"{total_distance:.0f}", f"{total_co2_avoided:.1f}"])

    t = Table(table_data, colWidths=[55, 120, 70, 55, 60, 75])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0a6b7a")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (3, 0), (-1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#ccc")),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#e8f5e9")),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 20))

    # Summary
    co2_avoided_t = total_co2_avoided / 1000
    equiv_flights = co2_avoided_t / params["co2_per_flight_paris_nyc"] if params["co2_per_flight_paris_nyc"] > 0 else 0
    equiv_containers = co2_avoided_t / params["co2_per_container_asia_eu"] if params["co2_per_container_asia_eu"] > 0 else 0

    elements.append(Paragraph(f"<b>Total CO₂ évité : {co2_avoided_t:.2f} tonnes</b>", bold_style))
    elements.append(Paragraph(
        f"Soit l'équivalent de {equiv_flights:.1f} vols Paris–New York ou {equiv_containers:.0f} containers Asie–Europe par voie conventionnelle.",
        body_style
    ))
    elements.append(Spacer(1, 20))

    elements.append(Paragraph(
        "Ce certificat est généré automatiquement par la plateforme my_TOWT sur la base des données "
        "de transport réelles. Les facteurs d'émission utilisés sont conformes aux standards IMO et EU MRV.",
        ParagraphStyle("Disclaimer", parent=body_style, fontSize=9, textColor=colors.HexColor("#999"))
    ))
    elements.append(Spacer(1, 30))
    elements.append(Paragraph("Pour TOWT — Transport à la Voile", bold_style))

    doc.build(elements)
    buf.seek(0)
    safe_name = client_name.replace(" ", "_").replace("/", "_")[:30]
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=certificat_decarbonation_{safe_name}_{current_year}.pdf"},
    )


# ─── LIST CLIENTS FOR CERTIFICATE SELECTOR ───────────────────
@router.get("/certificate/clients", response_class=HTMLResponse)
async def certificate_clients(
    request: Request,
    year: Optional[int] = Query(None),
    user: User = Depends(require_permission("kpi", "C")),
    db: AsyncSession = Depends(get_db),
):
    """Return list of clients with orders in given year for certificate generation."""
    current_year = year or datetime.now().year
    # Get distinct client names from orders assigned to legs in this year
    result = await db.execute(
        select(distinct(Order.client_name))
        .join(OrderAssignment, OrderAssignment.order_id == Order.id)
        .join(Leg, Leg.id == OrderAssignment.leg_id)
        .where(Leg.year == current_year, Order.client_name.isnot(None))
    )
    client_names = [r[0] for r in result.all() if r[0]]

    # Also get from Client table via rate_grid
    from app.models.commercial import RateGrid
    result2 = await db.execute(
        select(distinct(Client.company_name))
        .join(RateGrid, RateGrid.client_id == Client.id)
        .join(Order, Order.rate_grid_id == RateGrid.id)
        .join(OrderAssignment, OrderAssignment.order_id == Order.id)
        .join(Leg, Leg.id == OrderAssignment.leg_id)
        .where(Leg.year == current_year)
    )
    for r in result2.all():
        if r[0] and r[0] not in client_names:
            client_names.append(r[0])

    client_names.sort()

    # Return as simple HTML fragment (for HTMX)
    options = "".join(f'<option value="{c}">{c}</option>' for c in client_names)
    html = f'<select name="client_name" required style="padding:8px;border-radius:6px;border:1px solid #ccc;min-width:200px;font-family:Poppins,system-ui,sans-serif;">'
    html += '<option value="">— Sélectionner un client —</option>'
    html += options
    html += '</select>'
    return HTMLResponse(html)
