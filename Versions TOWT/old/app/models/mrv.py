"""Models for MRV (Monitoring, Reporting, Verification) fuel reporting module."""
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey, Text, Date, func
)
from sqlalchemy.orm import relationship
from app.database import Base


# ─── MRV EVENT TYPES ─────────────────────────────────────────
MRV_EVENT_TYPES = [
    ("departure", "Departure"),
    ("arrival", "Arrival"),
    ("at_sea", "At Sea"),
    ("begin_anchoring", "Begin Anchoring/Drifting"),
    ("end_anchoring", "End Anchoring/Drifting"),
]

# ─── SOF → MRV event type mapping ───────────────────────────
SOF_TO_MRV_MAP = {
    "EOSP": "departure",          # EOSP (fin de passage) → MRV Departure
    "SOSP": "arrival",            # SOSP (début de passage) → MRV Arrival
    "ANCHORED": "begin_anchoring",
    "ANCHOR_AWEIGH": "end_anchoring",
}


class MrvParameter(Base):
    """Global MRV configuration parameters."""
    __tablename__ = "mrv_parameters"

    id = Column(Integer, primary_key=True, autoincrement=True)
    parameter_name = Column(String(100), unique=True, nullable=False)
    parameter_value = Column(Float, nullable=False)
    unit = Column(String(50), nullable=True)
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# Default MRV parameters
MRV_DEFAULTS = {
    "avg_mdo_density": {"value": 0.845, "unit": "t/m³", "description": "Densité moyenne MDO (entre 0.82 et 0.87)"},
    "mdo_admissible_deviation": {"value": 2.0, "unit": "mt", "description": "Déviation admissible ROB (metric tons)"},
    "co2_emission_factor": {"value": 3.206, "unit": "t CO₂/t fuel", "description": "Facteur émission CO₂ par tonne MDO"},
}


class MrvEvent(Base):
    """MRV fuel reporting event linked to a leg."""
    __tablename__ = "mrv_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    leg_id = Column(Integer, ForeignKey("legs.id", ondelete="CASCADE"), nullable=False)
    sof_event_id = Column(Integer, ForeignKey("sof_events.id", ondelete="SET NULL"), nullable=True)

    # Event identification
    event_type = Column(String(30), nullable=False)  # from MRV_EVENT_TYPES
    timestamp_utc = Column(DateTime(timezone=True), nullable=False)

    # 4 DO Counters (running totals from start of ship exploitation)
    port_me_do_counter = Column(Float, nullable=True)     # Port Main Engine DO Counter
    stbd_me_do_counter = Column(Float, nullable=True)     # Starboard Main Engine DO Counter
    fwd_gen_do_counter = Column(Float, nullable=True)     # FWD Generator DO Counter
    aft_gen_do_counter = Column(Float, nullable=True)     # AFT Generator DO Counter

    # Declared values
    rob_mt = Column(Float, nullable=True)          # Remaining On Board (declared, metric tons)
    cargo_mrv_mt = Column(Float, nullable=True)    # Cargo MRV (displacement – lightship, metric tons)

    # Bunkering (departure events only)
    bunkering_qty_mt = Column(Float, nullable=True)   # Bunkering quantity in metric tons
    bunkering_date = Column(Date, nullable=True)       # Bunkering date

    # Position (from AIS/GPS tracking data)
    latitude_deg = Column(Integer, nullable=True)
    latitude_min = Column(Integer, nullable=True)
    latitude_ns = Column(String(1), nullable=True)     # "N" or "S"
    longitude_deg = Column(Integer, nullable=True)
    longitude_min = Column(Integer, nullable=True)
    longitude_ew = Column(String(1), nullable=True)    # "E" or "W"

    # Distance
    distance_nm = Column(Float, nullable=True)  # Distance from previous event (nautical miles)

    # Calculated fields (stored for performance)
    me_consumption_mdo = Column(Float, nullable=True)   # Main Engine consumption (metric tons)
    ae_consumption_mdo = Column(Float, nullable=True)   # Auxiliary Engine consumption (metric tons)
    total_consumption_mdo = Column(Float, nullable=True) # ME + AE
    rob_calculated = Column(Float, nullable=True)        # Calculated ROB for cross-check

    # Quality status
    quality_status = Column(String(10), default="pending")  # pending, ok, warning, error
    quality_notes = Column(Text, nullable=True)

    # Metadata
    created_by = Column(String(200), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    leg = relationship("Leg", backref="mrv_events")
    sof_event = relationship("SofEvent", backref="mrv_event")
