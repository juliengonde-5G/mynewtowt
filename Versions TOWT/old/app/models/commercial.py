from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean, Date, func, Enum
)
from sqlalchemy.orm import relationship
from app.database import Base
import enum
import json


class ClientType(str, enum.Enum):
    FREIGHT_FORWARDER = "freight_forwarder"
    SHIPPER = "shipper"


class Client(Base):
    """Commercial client (Freight Forwarder or Shipper)."""
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    client_type = Column(String(30), nullable=False)  # freight_forwarder | shipper
    contact_name = Column(String(200), nullable=True)
    contact_email = Column(String(200), nullable=True)
    contact_phone = Column(String(50), nullable=True)
    address = Column(Text, nullable=True)
    country = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    pipedrive_org_id = Column(Integer, nullable=True)  # Pipedrive Organization ID
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    rate_grids = relationship("RateGrid", back_populates="client", cascade="all, delete-orphan")
    rate_offers = relationship("RateOffer", back_populates="client", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Client {self.name} ({self.client_type})>"


class RateGridStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    EXPIRED = "expired"
    SUPERSEDED = "superseded"


# ─── Default volume brackets with degression coefficients ───
# For Shippers: degressive pricing based on volume per shipment
# For Freight Forwarders: flat rate (single bracket)
DEFAULT_BRACKETS_SHIPPER = [
    {"key": "lt50",   "label": "< 50 palettes",       "max_qty": 49,  "coeff": 1.10},
    {"key": "100",    "label": "100 palettes",         "max_qty": 100, "coeff": 1.00},
    {"key": "200",    "label": "200 palettes",         "max_qty": 200, "coeff": 0.80},
    {"key": "300",    "label": "300 palettes",         "max_qty": 300, "coeff": 0.80},
    {"key": "400",    "label": "400 palettes",         "max_qty": 400, "coeff": 0.80},
    {"key": "500",    "label": "500 palettes",         "max_qty": 500, "coeff": 0.70},
    {"key": "full",   "label": "Full ship (850 pal.)", "max_qty": 850, "coeff": 0.60},
]

DEFAULT_BRACKETS_FF = [
    {"key": "flat", "label": "Tarif unique", "max_qty": 99999, "coeff": 1.00},
]

# Legacy brackets for backward compat
PALETTE_BRACKETS = [
    {"key": "lt50",  "label": "< 50 palettes",  "min": 1, "max": 49},
    {"key": "100",   "label": "100 palettes",    "min": 50, "max": 100},
    {"key": "200",   "label": "200 palettes",    "min": 101, "max": 200},
    {"key": "300",   "label": "300 palettes",    "min": 201, "max": 300},
    {"key": "400",   "label": "400 palettes",    "min": 301, "max": 400},
    {"key": "500",   "label": "500 palettes",    "min": 401, "max": 500},
    {"key": "full",  "label": "Full ship (850)", "min": 501, "max": 850},
]


class RateGrid(Base):
    """
    Tariff grid for a client.
    - Freight Forwarder: flat rate per route (POL/POD) for a period
    - Shipper: degressive rate per route for a duration with volume brackets
    """
    __tablename__ = "rate_grids"

    id = Column(Integer, primary_key=True, autoincrement=True)
    reference = Column(String(50), unique=True, nullable=False, index=True)  # RG-2026-0001

    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    vessel_id = Column(Integer, ForeignKey("vessels.id"), nullable=True)  # For OPEX lookup

    # Validity period
    valid_from = Column(Date, nullable=False)
    valid_to = Column(Date, nullable=False)

    # Pricing parameters
    adjustment_index = Column(Float, default=1.0)  # Coefficient multiplicateur (1.0 = no change)
    bl_fee = Column(Float, default=0)  # BL fee (copied from company params at creation)
    booking_fee = Column(Float, default=0)  # Booking fee (copied from company params at creation)

    # Volume brackets stored as JSON — allows full customization
    # Format: [{"key":"lt50","label":"<50 pal.","max_qty":49,"coeff":1.10}, ...]
    brackets_json = Column(Text, nullable=True)

    # Shipper-specific: volume commitment per order
    volume_commitment = Column(Integer, nullable=True)  # Min palettes per order (shipper only)

    # Status
    status = Column(String(20), default=RateGridStatus.DRAFT.value)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by = Column(String(100), nullable=True)

    # Relationships
    client = relationship("Client", back_populates="rate_grids")
    vessel = relationship("Vessel")
    lines = relationship("RateGridLine", back_populates="rate_grid", cascade="all, delete-orphan",
                         order_by="RateGridLine.id")

    @property
    def brackets(self):
        """Parse brackets from JSON, with fallback to defaults."""
        if self.brackets_json:
            try:
                return json.loads(self.brackets_json)
            except (json.JSONDecodeError, TypeError):
                pass
        # Default based on client type
        if self.client and self.client.client_type == "freight_forwarder":
            return DEFAULT_BRACKETS_FF
        return DEFAULT_BRACKETS_SHIPPER

    @brackets.setter
    def brackets(self, value):
        self.brackets_json = json.dumps(value) if value else None

    @property
    def is_ff(self):
        return self.client and self.client.client_type == "freight_forwarder"

    def __repr__(self):
        return f"<RateGrid {self.reference} - {self.status}>"


class RateGridLine(Base):
    """
    One route (POL/POD) in a rate grid.
    Rates are stored as JSON to support variable number of brackets.
    Also keeps legacy columns for backward compatibility.

    Price formula: base_rate = opex_daily * nav_days / 850
    Each bracket rate = base_rate * bracket_coeff * adjustment_index
    """
    __tablename__ = "rate_grid_lines"

    id = Column(Integer, primary_key=True, autoincrement=True)
    rate_grid_id = Column(Integer, ForeignKey("rate_grids.id"), nullable=False)

    pol_locode = Column(String(5), ForeignKey("ports.locode"), nullable=False)
    pod_locode = Column(String(5), ForeignKey("ports.locode"), nullable=False)

    # Source leg (from sailing schedule)
    leg_id = Column(Integer, ForeignKey("legs.id"), nullable=True)

    # Navigation data (computed or manual)
    distance_nm = Column(Float, nullable=True)  # Orthodromic distance
    nav_days = Column(Float, nullable=True)  # distance / (8 * 24)
    opex_daily = Column(Float, nullable=True)  # OPEX journalier used for calculation

    # Base rate per palette (before brackets — formula result for 1 palette)
    base_rate = Column(Float, nullable=True)

    # Bracket rates stored as JSON: {"lt50": 285.50, "100": 259.55, ...}
    rates_json = Column(Text, nullable=True)

    # Legacy 4-bracket columns (kept for backward compat)
    rate_lt10 = Column(Float, nullable=True)
    rate_10to50 = Column(Float, nullable=True)
    rate_51to100 = Column(Float, nullable=True)
    rate_gt100 = Column(Float, nullable=True)

    # Manual override flag
    is_manual = Column(Boolean, default=False)

    # Relationships
    rate_grid = relationship("RateGrid", back_populates="lines")
    pol = relationship("Port", foreign_keys=[pol_locode])
    pod = relationship("Port", foreign_keys=[pod_locode])
    leg = relationship("Leg", foreign_keys=[leg_id])

    @property
    def rates(self):
        if self.rates_json:
            try:
                return json.loads(self.rates_json)
            except (json.JSONDecodeError, TypeError):
                pass
        return {}

    @rates.setter
    def rates(self, value):
        self.rates_json = json.dumps(value) if value else None

    def compute_rates(self, opex_daily: float, adjustment_index: float = 1.0,
                      brackets=None):
        """
        Compute rates from formula:
        base_rate = opex_daily * nav_days / 850
        Each bracket_rate = base_rate * coeff * adjustment_index
        """
        if not self.distance_nm or not opex_daily:
            return
        self.opex_daily = opex_daily
        self.nav_days = round(self.distance_nm / (8 * 24), 2)
        self.base_rate = round(opex_daily * self.nav_days / 850, 2)

        adj = adjustment_index or 1.0
        computed = {}

        if brackets:
            for b in brackets:
                computed[b["key"]] = round(self.base_rate * b["coeff"] * adj, 2)
        else:
            # Fallback to default shipper brackets
            for b in DEFAULT_BRACKETS_SHIPPER:
                computed[b["key"]] = round(self.base_rate * b["coeff"] * adj, 2)

        self.rates = computed

        # Also fill legacy columns for backward compat
        self.rate_lt10 = computed.get("lt50", computed.get("lt10"))
        self.rate_10to50 = computed.get("100", computed.get("10to50"))
        self.rate_51to100 = computed.get("200", computed.get("51to100"))
        self.rate_gt100 = computed.get("full", computed.get("gt100"))

    def get_rate_for_quantity(self, qty: int) -> float:
        """Return the per-palette rate for a given quantity using bracket rates."""
        rates = self.rates
        if not rates:
            # Fallback to legacy columns
            if qty < 50:
                return self.rate_lt10 or 0
            elif qty <= 100:
                return self.rate_10to50 or 0
            elif qty <= 200:
                return self.rate_51to100 or 0
            else:
                return self.rate_gt100 or 0

        # Use JSON rates with bracket matching
        if "flat" in rates:
            return rates["flat"]
        if qty < 50:
            return rates.get("lt50", 0)
        elif qty <= 100:
            return rates.get("100", 0)
        elif qty <= 200:
            return rates.get("200", 0)
        elif qty <= 300:
            return rates.get("300", 0)
        elif qty <= 400:
            return rates.get("400", 0)
        elif qty <= 500:
            return rates.get("500", 0)
        else:
            return rates.get("full", 0)

    def __repr__(self):
        return f"<RateGridLine {self.pol_locode} → {self.pod_locode}>"


class RateOfferStatus(str, enum.Enum):
    DRAFT = "draft"
    SENT = "sent"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"


class RateOffer(Base):
    """
    Rate offer document sent to a shipper client.
    Links to a rate grid and stores document generation metadata.
    """
    __tablename__ = "rate_offers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    reference = Column(String(50), unique=True, nullable=False, index=True)  # RO-2026-0001

    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    rate_grid_id = Column(Integer, ForeignKey("rate_grids.id"), nullable=False)

    # Offer details
    validity_date = Column(Date, nullable=False)  # Date limite de validité
    status = Column(String(20), default=RateOfferStatus.DRAFT.value)

    # Document
    document_filename = Column(String(255), nullable=True)
    document_path = Column(String(500), nullable=True)

    notes = Column(Text, nullable=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    pipedrive_deal_id = Column(Integer, nullable=True)  # Pipedrive Deal ID
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(String(100), nullable=True)

    # Relationships
    client = relationship("Client", back_populates="rate_offers")
    rate_grid = relationship("RateGrid")

    def __repr__(self):
        return f"<RateOffer {self.reference} → {self.client_id}>"
