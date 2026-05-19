"""
Stowage Plan models — vessel zone structure and batch-to-zone assignments.

VESSEL STRUCTURE (identical for all 4 vessels: Anemos, Artemis, Atlantis, Atlas)
================================================================================
The vessel has 2 holds (cales), 3 decks (ponts) per hold, and 3 blocks per deck = 18 zones.

Naming convention: {DECK}_{HOLD}_{BLOCK}
  DECK:  INF (lower/inférieure), MIL (middle/intermédiaire), SUP (upper/supérieure)
  HOLD:  AR (aft/arrière), AV (forward/avant)
  BLOCK: AR (aft/arrière), MIL (middle/milieu), AV (forward/avant)

Loading order: aft→forward, then bottom→top (INF_AR_AR=1 → SUP_AV_AV=18)
Exception: dangerous goods (IMO class) and oversized cargo → forced to SUP_AV_AR/MIL/AV

BASKET (PANIER) DIMENSIONS
===========================
  Surface libre: 380 x 150 cm
  Hauteur: 2.2 m
  CMU: 5.1 t
  Poids vide: 2.2 t
  Any pallet exceeding these dimensions must go to SUP_AV zones.

TECHNICAL REFERENCE
===================
  Source: easy_chargement_navire_complet.xlsx (committed in project root)
  Surfaces and deck resistances are fixed structural properties of the vessels.
"""

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey, Text, func
)
from sqlalchemy.orm import relationship
from app.database import Base


# ═══════════════════════════════════════════════════════════════
# PALLET FORMATS — dimensions and capacity per zone
# ═══════════════════════════════════════════════════════════════

PALLET_FORMATS = [
    {"value": "EPAL", "label": "Europalette (120×80)", "length_cm": 120, "width_cm": 80},
    {"value": "USPAL", "label": "US Pallet (120×100)", "length_cm": 120, "width_cm": 100},
    {"value": "PORTPAL", "label": "Palette Portuaire", "length_cm": 120, "width_cm": 100},
    {"value": "IBC", "label": "IBC (+6cm)", "length_cm": 120, "width_cm": 106},
    {"value": "BIGBAG", "label": "Big Bag Palettisé (+3cm)", "length_cm": 120, "width_cm": 103},
    {"value": "BARRIQUE120", "label": "Barrique 120×120 (+3cm)", "length_cm": 123, "width_cm": 123},
    {"value": "BARRIQUE140", "label": "Barrique 140×140 (+3cm)", "length_cm": 143, "width_cm": 143},
]

PALLET_FORMAT_MAP = {f["value"]: f for f in PALLET_FORMATS}


# ═══════════════════════════════════════════════════════════════
# BASKET (PANIER) CONSTRAINTS
# ═══════════════════════════════════════════════════════════════

BASKET_LENGTH_CM = 380
BASKET_WIDTH_CM = 150
BASKET_HEIGHT_M = 2.2
BASKET_CMU_T = 5.1
BASKET_TARE_T = 2.2


# ═══════════════════════════════════════════════════════════════
# ZONE DEFINITIONS — 18 zones, fixed for all vessels
# ═══════════════════════════════════════════════════════════════

# Loading order: aft→forward, bottom→top
LOADING_ORDER = [
    "INF_AR_AR", "INF_AR_MIL", "INF_AR_AV",
    "INF_AV_AR", "INF_AV_MIL", "INF_AV_AV",
    "MIL_AR_AR", "MIL_AR_MIL", "MIL_AR_AV",
    "MIL_AV_AR", "MIL_AV_MIL", "MIL_AV_AV",
    "SUP_AR_AR", "SUP_AR_MIL", "SUP_AR_AV",
    "SUP_AV_AR", "SUP_AV_MIL", "SUP_AV_AV",
]

# Zones reserved for dangerous goods and oversized cargo
DANGEROUS_ZONES = ["SUP_AV_AR", "SUP_AV_MIL", "SUP_AV_AV"]

# Zone structure: {zone_code: {deck, hold, block, surface_m2, resistance_t_m2, deck_label, ...}}
# Source: easy_chargement_navire_complet.xlsx — ZONES + per-pallet-type sheets
# Surfaces and resistances are from the pallet EU sheet (identical across pallet types).

ZONE_DEFINITIONS = {
    # ─── CALE INFÉRIEURE (Lower hold) ───────────────────────
    "INF_AR_AR": {
        "deck": "INF", "hold": "AR", "block": "AR",
        "deck_label_fr": "Cale inférieure", "deck_label_en": "Lower hold",
        "hold_label_fr": "Arrière", "hold_label_en": "Aft",
        "block_label_fr": "Bloc arrière", "block_label_en": "Aft block",
        "surface_m2": 20, "resistance_t_m2": 2.5,
    },
    "INF_AR_MIL": {
        "deck": "INF", "hold": "AR", "block": "MIL",
        "deck_label_fr": "Cale inférieure", "deck_label_en": "Lower hold",
        "hold_label_fr": "Arrière", "hold_label_en": "Aft",
        "block_label_fr": "Bloc milieu", "block_label_en": "Middle block",
        "surface_m2": 56, "resistance_t_m2": 2.5,
    },
    "INF_AR_AV": {
        "deck": "INF", "hold": "AR", "block": "AV",
        "deck_label_fr": "Cale inférieure", "deck_label_en": "Lower hold",
        "hold_label_fr": "Arrière", "hold_label_en": "Aft",
        "block_label_fr": "Bloc avant", "block_label_en": "Forward block",
        "surface_m2": 68, "resistance_t_m2": 2.5,
    },
    "INF_AV_AR": {
        "deck": "INF", "hold": "AV", "block": "AR",
        "deck_label_fr": "Cale inférieure", "deck_label_en": "Lower hold",
        "hold_label_fr": "Avant", "hold_label_en": "Forward",
        "block_label_fr": "Bloc arrière", "block_label_en": "Aft block",
        "surface_m2": 66, "resistance_t_m2": 2.5,
    },
    "INF_AV_MIL": {
        "deck": "INF", "hold": "AV", "block": "MIL",
        "deck_label_fr": "Cale inférieure", "deck_label_en": "Lower hold",
        "hold_label_fr": "Avant", "hold_label_en": "Forward",
        "block_label_fr": "Bloc milieu", "block_label_en": "Middle block",
        "surface_m2": 59, "resistance_t_m2": 2.5,
    },
    "INF_AV_AV": {
        "deck": "INF", "hold": "AV", "block": "AV",
        "deck_label_fr": "Cale inférieure", "deck_label_en": "Lower hold",
        "hold_label_fr": "Avant", "hold_label_en": "Forward",
        "block_label_fr": "Bloc avant", "block_label_en": "Forward block",
        "surface_m2": 64, "resistance_t_m2": 2.5,
    },

    # ─── CALE INTERMÉDIAIRE (Middle hold) ───────────────────
    "MIL_AR_AR": {
        "deck": "MIL", "hold": "AR", "block": "AR",
        "deck_label_fr": "Cale intermédiaire", "deck_label_en": "Middle hold",
        "hold_label_fr": "Arrière", "hold_label_en": "Aft",
        "block_label_fr": "Bloc arrière", "block_label_en": "Aft block",
        "surface_m2": 62, "resistance_t_m2": 2.0,
    },
    "MIL_AR_MIL": {
        "deck": "MIL", "hold": "AR", "block": "MIL",
        "deck_label_fr": "Cale intermédiaire", "deck_label_en": "Middle hold",
        "hold_label_fr": "Arrière", "hold_label_en": "Aft",
        "block_label_fr": "Bloc milieu", "block_label_en": "Middle block",
        "surface_m2": 61, "resistance_t_m2": 1.3,
    },
    "MIL_AR_AV": {
        "deck": "MIL", "hold": "AR", "block": "AV",
        "deck_label_fr": "Cale intermédiaire", "deck_label_en": "Middle hold",
        "hold_label_fr": "Arrière", "hold_label_en": "Aft",
        "block_label_fr": "Bloc avant", "block_label_en": "Forward block",
        "surface_m2": 69, "resistance_t_m2": 2.0,
    },
    "MIL_AV_AR": {
        "deck": "MIL", "hold": "AV", "block": "AR",
        "deck_label_fr": "Cale intermédiaire", "deck_label_en": "Middle hold",
        "hold_label_fr": "Avant", "hold_label_en": "Forward",
        "block_label_fr": "Bloc arrière", "block_label_en": "Aft block",
        "surface_m2": 69, "resistance_t_m2": 2.0,
    },
    "MIL_AV_MIL": {
        "deck": "MIL", "hold": "AV", "block": "MIL",
        "deck_label_fr": "Cale intermédiaire", "deck_label_en": "Middle hold",
        "hold_label_fr": "Avant", "hold_label_en": "Forward",
        "block_label_fr": "Bloc milieu", "block_label_en": "Middle block",
        "surface_m2": 57, "resistance_t_m2": 1.3,
    },
    "MIL_AV_AV": {
        "deck": "MIL", "hold": "AV", "block": "AV",
        "deck_label_fr": "Cale intermédiaire", "deck_label_en": "Middle hold",
        "hold_label_fr": "Avant", "hold_label_en": "Forward",
        "block_label_fr": "Bloc avant", "block_label_en": "Forward block",
        "surface_m2": 70, "resistance_t_m2": 1.0,
    },

    # ─── CALE SUPÉRIEURE (Upper hold) ───────────────────────
    "SUP_AR_AR": {
        "deck": "SUP", "hold": "AR", "block": "AR",
        "deck_label_fr": "Cale supérieure", "deck_label_en": "Upper hold",
        "hold_label_fr": "Arrière", "hold_label_en": "Aft",
        "block_label_fr": "Bloc arrière", "block_label_en": "Aft block",
        "surface_m2": 73, "resistance_t_m2": 1.0,
    },
    "SUP_AR_MIL": {
        "deck": "SUP", "hold": "AR", "block": "MIL",
        "deck_label_fr": "Cale supérieure", "deck_label_en": "Upper hold",
        "hold_label_fr": "Arrière", "hold_label_en": "Aft",
        "block_label_fr": "Bloc milieu", "block_label_en": "Middle block",
        "surface_m2": 61, "resistance_t_m2": 1.0,
    },
    "SUP_AR_AV": {
        "deck": "SUP", "hold": "AR", "block": "AV",
        "deck_label_fr": "Cale supérieure", "deck_label_en": "Upper hold",
        "hold_label_fr": "Arrière", "hold_label_en": "Aft",
        "block_label_fr": "Bloc avant", "block_label_en": "Forward block",
        "surface_m2": 73, "resistance_t_m2": 1.0,
    },
    "SUP_AV_AR": {
        "deck": "SUP", "hold": "AV", "block": "AR",
        "deck_label_fr": "Cale supérieure", "deck_label_en": "Upper hold",
        "hold_label_fr": "Avant", "hold_label_en": "Forward",
        "block_label_fr": "Bloc arrière", "block_label_en": "Aft block",
        "surface_m2": 73, "resistance_t_m2": 1.0,
    },
    "SUP_AV_MIL": {
        "deck": "SUP", "hold": "AV", "block": "MIL",
        "deck_label_fr": "Cale supérieure", "deck_label_en": "Upper hold",
        "hold_label_fr": "Avant", "hold_label_en": "Forward",
        "block_label_fr": "Bloc milieu", "block_label_en": "Middle block",
        "surface_m2": 61, "resistance_t_m2": 1.0,
    },
    "SUP_AV_AV": {
        "deck": "SUP", "hold": "AV", "block": "AV",
        "deck_label_fr": "Cale supérieure", "deck_label_en": "Upper hold",
        "hold_label_fr": "Avant", "hold_label_en": "Forward",
        "block_label_fr": "Bloc avant", "block_label_en": "Forward block",
        "surface_m2": 76, "resistance_t_m2": 1.0,
    },
}

# ═══════════════════════════════════════════════════════════════
# PALLET CAPACITIES PER ZONE PER FORMAT
# Source: easy_chargement_navire_complet.xlsx (each pallet-type sheet)
# Values: (simple_count, stacked_count)
# ═══════════════════════════════════════════════════════════════

ZONE_CAPACITIES = {
    # zone_code → {pallet_format → (simple, stacked)}
    "INF_AR_AR":  {"EPAL": (20, 40), "USPAL": (12, 24), "IBC": (16, None), "BIGBAG": (16, 24), "BARRIQUE120": (12, None), "BARRIQUE140": (9, None), "PORTPAL": (12, 24)},
    "INF_AR_MIL": {"EPAL": (36, 50), "USPAL": (31, 62), "IBC": (33, None), "BIGBAG": (33, 62), "BARRIQUE120": (26, None), "BARRIQUE140": (18, None), "PORTPAL": (31, 62)},
    "INF_AR_AV":  {"EPAL": (68, 106), "USPAL": (37, 74), "IBC": (49, None), "BIGBAG": (49, 74), "BARRIQUE120": (39, None), "BARRIQUE140": (30, None), "PORTPAL": (37, 74)},
    "INF_AV_AR":  {"EPAL": (65, 125), "USPAL": (38, 58), "IBC": (46, None), "BIGBAG": (48, 58), "BARRIQUE120": (40, None), "BARRIQUE140": (26, None), "PORTPAL": (38, 58)},
    "INF_AV_MIL": {"EPAL": (38, 68), "USPAL": (30, 60), "IBC": (31, None), "BIGBAG": (31, 60), "BARRIQUE120": (26, None), "BARRIQUE140": (19, None), "PORTPAL": (30, 60)},
    "INF_AV_AV":  {"EPAL": (56, 106), "USPAL": (37, 74), "IBC": (42, None), "BIGBAG": (44, 74), "BARRIQUE120": (36, None), "BARRIQUE140": (25, None), "PORTPAL": (37, 74)},

    "MIL_AR_AR":  {"EPAL": (58, 108), "USPAL": (41, 80), "IBC": (43, None), "BIGBAG": (45, 80), "BARRIQUE120": (38, None), "BARRIQUE140": (26, None), "PORTPAL": (41, 80)},
    "MIL_AR_MIL": {"EPAL": (39, 60), "USPAL": (27, 54), "IBC": (33, None), "BIGBAG": (33, 54), "BARRIQUE120": (26, None), "BARRIQUE140": (26, None), "PORTPAL": (27, 54)},
    "MIL_AR_AV":  {"EPAL": (69, 129), "USPAL": (42, 84), "IBC": (50, None), "BIGBAG": (53, 84), "BARRIQUE120": (43, None), "BARRIQUE140": (30, None), "PORTPAL": (42, 84)},
    "MIL_AV_AR":  {"EPAL": (68, 128), "USPAL": (42, 38), "IBC": (48, None), "BIGBAG": (52, 38), "BARRIQUE120": (43, None), "BARRIQUE140": (31, None), "PORTPAL": (42, 38)},
    "MIL_AV_MIL": {"EPAL": (42, 84), "USPAL": (30, 60), "IBC": (32, None), "BIGBAG": (33, 60), "BARRIQUE120": (25, None), "BARRIQUE140": (21, None), "PORTPAL": (30, 60)},
    "MIL_AV_AV":  {"EPAL": (56, 106), "USPAL": (39, 78), "IBC": (43, None), "BIGBAG": (44, 78), "BARRIQUE120": (39, None), "BARRIQUE140": (24, None), "PORTPAL": (39, 78)},

    "SUP_AR_AR":  {"EPAL": (69, 129), "USPAL": (47, 87), "IBC": (51, None), "BIGBAG": (54, 87), "BARRIQUE120": (45, None), "BARRIQUE140": (31, None), "PORTPAL": (47, 87)},
    "SUP_AR_MIL": {"EPAL": (39, 60), "USPAL": (20, 40), "IBC": (24, None), "BIGBAG": (27, 40), "BARRIQUE120": (22, None), "BARRIQUE140": (20, None), "PORTPAL": (20, 40)},
    "SUP_AR_AV":  {"EPAL": (69, 129), "USPAL": (44, 80), "IBC": (52, None), "BIGBAG": (54, 80), "BARRIQUE120": (43, None), "BARRIQUE140": (31, None), "PORTPAL": (44, 80)},
    "SUP_AV_AR":  {"EPAL": (68, 112), "USPAL": (42, 83), "IBC": (52, None), "BIGBAG": (52, 83), "BARRIQUE120": (43, None), "BARRIQUE140": (31, None), "PORTPAL": (42, 83)},
    "SUP_AV_MIL": {"EPAL": (40, 74), "USPAL": (23, 46), "IBC": (25, None), "BIGBAG": (27, 46), "BARRIQUE120": (22, None), "BARRIQUE140": (19, None), "PORTPAL": (23, 46)},
    "SUP_AV_AV":  {"EPAL": (72, 108), "USPAL": (44, 80), "IBC": (53, None), "BIGBAG": (55, 80), "BARRIQUE120": (46, None), "BARRIQUE140": (28, None), "PORTPAL": (44, 80)},
}


# ═══════════════════════════════════════════════════════════════
# IMO HAZARD CLASSES
# ═══════════════════════════════════════════════════════════════

IMO_CLASSES = [
    ("1", "Classe 1 - Matières explosives / Explosives"),
    ("1.1", "1.1 - Danger d'explosion en masse / Mass explosion hazard"),
    ("1.2", "1.2 - Danger de projection / Projection hazard"),
    ("1.3", "1.3 - Danger d'incendie / Fire hazard"),
    ("1.4", "1.4 - Danger mineur / Minor hazard"),
    ("1.5", "1.5 - Matières très peu sensibles / Very insensitive"),
    ("1.6", "1.6 - Objets extrêmement peu sensibles / Extremely insensitive"),
    ("2", "Classe 2 - Gaz / Gases"),
    ("2.1", "2.1 - Gaz inflammables / Flammable gases"),
    ("2.2", "2.2 - Gaz non inflammables / Non-flammable gases"),
    ("2.3", "2.3 - Gaz toxiques / Toxic gases"),
    ("3", "Classe 3 - Liquides inflammables / Flammable liquids"),
    ("4", "Classe 4 - Matières solides inflammables / Flammable solids"),
    ("4.1", "4.1 - Solides inflammables / Flammable solids"),
    ("4.2", "4.2 - Combustion spontanée / Spontaneous combustion"),
    ("4.3", "4.3 - Dangereux au contact de l'eau / Dangerous when wet"),
    ("5", "Classe 5 - Comburants et peroxydes / Oxidizers & peroxides"),
    ("5.1", "5.1 - Comburants / Oxidizing substances"),
    ("5.2", "5.2 - Peroxydes organiques / Organic peroxides"),
    ("6", "Classe 6 - Matières toxiques / Toxic substances"),
    ("6.1", "6.1 - Toxiques / Toxic"),
    ("6.2", "6.2 - Matières infectieuses / Infectious"),
    ("7", "Classe 7 - Matières radioactives / Radioactive"),
    ("8", "Classe 8 - Matières corrosives / Corrosives"),
    ("9", "Classe 9 - Matières dangereuses diverses / Miscellaneous"),
]


# ═══════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════

def get_zone_capacity(zone_code: str, pallet_format: str, stackable: bool = False) -> int:
    """Get max pallet count for a zone given pallet format and stacking preference."""
    caps = ZONE_CAPACITIES.get(zone_code, {}).get(pallet_format)
    if not caps:
        return 0
    simple, stacked = caps
    if stackable and stacked is not None:
        return stacked
    return simple


def get_zone_max_weight(zone_code: str) -> float:
    """Get max weight in tonnes for a zone (surface * resistance)."""
    zdef = ZONE_DEFINITIONS.get(zone_code)
    if not zdef:
        return 0
    return zdef["surface_m2"] * zdef["resistance_t_m2"]


def is_oversized(length_cm: float, width_cm: float, height_cm: float) -> bool:
    """Check if a pallet exceeds basket dimensions."""
    if not length_cm or not width_cm or not height_cm:
        return False
    # Check both orientations
    fits_normal = (length_cm <= BASKET_LENGTH_CM and width_cm <= BASKET_WIDTH_CM)
    fits_rotated = (width_cm <= BASKET_LENGTH_CM and length_cm <= BASKET_WIDTH_CM)
    height_ok = (height_cm / 100) <= BASKET_HEIGHT_M
    return not ((fits_normal or fits_rotated) and height_ok)


def is_dangerous(imo_class: str) -> bool:
    """Check if an IMO class indicates dangerous goods."""
    return bool(imo_class and imo_class.strip())


def must_go_sup_av(batch) -> bool:
    """Check if a batch must be placed in SUP_AV zones (dangerous or oversized)."""
    dangerous = is_dangerous(getattr(batch, 'imo_product_class', None))
    oversized = is_oversized(
        getattr(batch, 'length_cm', None) or 0,
        getattr(batch, 'width_cm', None) or 0,
        getattr(batch, 'height_cm', None) or 0,
    )
    return dangerous or oversized


def suggest_zone(batch, occupied: dict, pallet_format: str = "EPAL") -> str:
    """
    Suggest the best zone for a batch based on loading order rules.

    Args:
        batch: PackingListBatch object
        occupied: dict {zone_code: {"palettes": int, "weight_kg": float}} of current occupation
        pallet_format: pallet format code

    Returns:
        zone_code or None if no zone fits
    """
    stackable = (getattr(batch, 'stackable', '') or '').lower() in ('oui', 'yes', 'true', '1')
    qty = getattr(batch, 'pallet_quantity', 0) or 0
    weight = (getattr(batch, 'weight_kg', 0) or 0) * qty  # total weight

    # Determine zone candidates
    if must_go_sup_av(batch):
        candidates = DANGEROUS_ZONES
    else:
        candidates = [z for z in LOADING_ORDER if z not in DANGEROUS_ZONES]

    for zone_code in candidates:
        capacity = get_zone_capacity(zone_code, pallet_format, stackable)
        max_weight = get_zone_max_weight(zone_code) * 1000  # convert to kg

        current = occupied.get(zone_code, {"palettes": 0, "weight_kg": 0})
        remaining_palettes = capacity - current["palettes"]
        remaining_weight = max_weight - current["weight_kg"]

        if remaining_palettes >= qty and remaining_weight >= weight:
            return zone_code

    # Fallback: if dangerous/oversized zones are full, return None
    return None


def get_zone_label(zone_code: str, lang: str = "fr") -> str:
    """Get human-readable label for a zone."""
    zdef = ZONE_DEFINITIONS.get(zone_code)
    if not zdef:
        return zone_code
    if lang == "en":
        return f"{zdef['deck_label_en']} - {zdef['hold_label_en']} - {zdef['block_label_en']}"
    return f"{zdef['deck_label_fr']} - {zdef['hold_label_fr']} - {zdef['block_label_fr']}"


# ═══════════════════════════════════════════════════════════════
# DATABASE MODELS
# ═══════════════════════════════════════════════════════════════

class StowagePlan(Base):
    """Assignment of a packing list batch to a vessel zone for a specific leg."""
    __tablename__ = "stowage_plans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    leg_id = Column(Integer, ForeignKey("legs.id", ondelete="CASCADE"), nullable=False, index=True)
    batch_id = Column(Integer, ForeignKey("packing_list_batches.id", ondelete="CASCADE"), nullable=False, index=True)
    zone_code = Column(String(20), nullable=False)  # e.g. "INF_AR_MIL"

    # Snapshot at assignment time (for audit and claims)
    pallet_quantity = Column(Integer, nullable=True)
    pallet_format = Column(String(20), nullable=True)
    weight_total_kg = Column(Float, nullable=True)
    is_dangerous = Column(Integer, default=0)  # 0/1
    imo_class = Column(String(20), nullable=True)
    is_oversized = Column(Integer, default=0)  # 0/1
    stackable = Column(Integer, default=0)  # 0/1

    # Assignment metadata
    assigned_by = Column(String(200), nullable=True)
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    leg = relationship("Leg", backref="stowage_plans")
    batch = relationship("PackingListBatch", backref="stowage_plan")
