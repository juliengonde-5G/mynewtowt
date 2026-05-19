"""Centralized notification system for my_TOWT.

Creates OnboardNotification records and optionally ActivityLog entries
for company-wide events (arrival, departure, order confirmation, etc.).
"""
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.onboard import OnboardNotification


async def create_notification(
    db: AsyncSession,
    leg_id: int,
    category: str,
    title: str,
    detail: str = None,
):
    """Create a single OnboardNotification."""
    notif = OnboardNotification(
        leg_id=leg_id,
        category=category,
        title=title,
        detail=detail,
    )
    db.add(notif)
    return notif


async def notify_arrival(db: AsyncSession, leg, vessel_name: str, port_name: str):
    """Notify company: vessel has arrived at port (ATA set)."""
    ata_str = leg.ata.strftime("%d/%m/%Y %H:%M") if leg.ata else "—"
    title = f"Arrivée à quai — {vessel_name} à {port_name}"
    detail = (
        f"Le {vessel_name} est arrivé à {port_name} le {ata_str} UTC.\n"
        f"Leg: {leg.leg_code}\n"
        f"Les dates d'escale et le planning ont été mis à jour.\n"
        f"Le calcul économique du leg a été recalculé avec la durée réelle de navigation."
    )
    return await create_notification(db, leg.id, "escale", title, detail)


async def notify_departure(db: AsyncSession, leg, vessel_name: str, port_name: str):
    """Notify company: vessel has departed from port (ATD set)."""
    atd_str = leg.atd.strftime("%d/%m/%Y %H:%M") if leg.atd else "—"
    title = f"Départ — {vessel_name} de {port_name}"
    detail = (
        f"Le {vessel_name} a quitté {port_name} le {atd_str} UTC.\n"
        f"Leg: {leg.leg_code}\n"
        f"Le planning des legs suivants a été mis à jour."
    )
    return await create_notification(db, leg.id, "escale", title, detail)


async def notify_order_confirmed(
    db: AsyncSession,
    leg_id: int,
    order_ref: str,
    client_name: str,
    cargo_desc: str,
):
    """Notify operations: a transport order has been confirmed."""
    title = f"Commande confirmée — {order_ref} ({client_name})"
    detail = (
        f"L'ordre de transport {order_ref} pour {client_name} a été confirmé.\n"
        f"Cargo: {cargo_desc}\n"
        f"La préparation des documents cargo peut commencer."
    )
    return await create_notification(db, leg_id, "cargo", title, detail)


async def notify_cargo_doc_created(
    db: AsyncSession,
    leg_id: int,
    doc_type: str,
    order_ref: str,
):
    """Notify operations: a packing list has been created for a confirmed order."""
    title = f"Packing list créée — {order_ref}"
    detail = (
        f"Une packing list a été initialisée pour la commande {order_ref}.\n"
        f"Les éléments sont à compléter par le client ou l'opérateur."
    )
    return await create_notification(db, leg_id, "cargo", title, detail)


async def notify_delay(
    db: AsyncSession,
    leg,
    vessel_name: str,
    shift_hours: float,
    field: str = "eta",
):
    """Notify company when ETA/ETD shifts by more than 4h vs reference schedule."""
    direction = "retard" if shift_hours > 0 else "avance"
    abs_hours = abs(shift_hours)
    field_label = "ETA" if field == "eta" else "ETD"
    title = f"Décalage {field_label} — {vessel_name} ({direction} {abs_hours:.0f}h)"
    detail = (
        f"Le {field_label} du leg {leg.leg_code} a été décalé de {shift_hours:+.1f} heures par rapport au planning de référence.\n"
        f"Navire: {vessel_name}\n"
        f"Ce décalage dépasse le seuil de 4h et peut impacter les escales suivantes.\n"
        f"Veuillez vérifier le planning et informer les agents portuaires concernés."
    )
    return await create_notification(db, leg.id, "escale", title, detail)


async def notify_cargo_progress(
    db: AsyncSession,
    leg_id: int,
    order_ref: str,
    field_name: str,
    completion_pct: int,
):
    """Notify operations: packing list element has been filled."""
    title = f"Cargo doc — {order_ref} ({completion_pct}% complété)"
    detail = (
        f"Le champ '{field_name}' de la packing list pour {order_ref} a été renseigné.\n"
        f"Complétion: {completion_pct}%"
    )
    return await create_notification(db, leg_id, "cargo", title, detail)
