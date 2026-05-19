from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey, Text, func
)
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class LegStatus(str, enum.Enum):
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Leg(Base):
    __tablename__ = "legs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    leg_code = Column(String(20), unique=True, nullable=False, index=True)
    # Format: SHIPCODE + LETTER + DEP_COUNTRY + ARR_COUNTRY + YEAR_LAST_DIGIT
    # Example: 1CFRBR6 = Anemos, 3rd call, France->Brazil, 2026

    vessel_id = Column(Integer, ForeignKey("vessels.id"), nullable=False)
    year = Column(Integer, nullable=False)
    sequence = Column(Integer, nullable=False)  # Rang dans l'annee (1=A, 2=B, etc.)

    # Ports
    departure_port_locode = Column(String(5), ForeignKey("ports.locode"), nullable=False)
    arrival_port_locode = Column(String(5), ForeignKey("ports.locode"), nullable=False)

    # Planning - Reference (original schedule)
    etd_ref = Column(DateTime(timezone=True), nullable=True)  # Original ETD at booking time
    eta_ref = Column(DateTime(timezone=True), nullable=True)  # Original ETA at booking time

    # Planning - Previsionnel (updated estimates)
    eta = Column(DateTime(timezone=True), nullable=True)  # Estimated Time of Arrival
    etd = Column(DateTime(timezone=True), nullable=True)  # Estimated Time of Departure

    # Planning - Realise
    ata = Column(DateTime(timezone=True), nullable=True)  # Actual Time of Arrival
    atd = Column(DateTime(timezone=True), nullable=True)  # Actual Time of Departure

    # Navigation
    distance_nm = Column(Float, nullable=True)  # Distance orthodromique en milles nautiques
    speed_knots = Column(Float, nullable=True)  # Vitesse d'exploitation en noeuds
    elongation_coeff = Column(Float, default=1.25)  # Coefficient d'elongation
    computed_distance = Column(Float, nullable=True)  # distance_nm * elongation_coeff
    estimated_duration_hours = Column(Float, nullable=True)  # computed_distance / speed_knots

    # Status
    status = Column(String(20), default=LegStatus.PLANNED.value)
    notes = Column(Text, nullable=True)
    port_stay_days = Column(Integer, default=3)  # Durée d'escale en jours (entre ETA et ETD suivant)

    # Closure workflow: open → review → approved → locked
    closure_status = Column(String(20), default="open")
    closure_reviewed_by = Column(String(200), nullable=True)
    closure_reviewed_at = Column(DateTime(timezone=True), nullable=True)
    closure_approved_by = Column(String(200), nullable=True)
    closure_approved_at = Column(DateTime(timezone=True), nullable=True)
    closure_notes = Column(Text, nullable=True)
    closure_pdf_path = Column(String(500), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    vessel = relationship("Vessel", back_populates="legs")
    departure_port = relationship("Port", foreign_keys=[departure_port_locode])
    arrival_port = relationship("Port", foreign_keys=[arrival_port_locode])
    order_assignments = relationship("OrderAssignment", back_populates="leg", cascade="all, delete-orphan")
    operations = relationship("EscaleOperation", back_populates="leg", cascade="all, delete-orphan")
    docker_shifts = relationship("DockerShift", back_populates="leg", cascade="all, delete-orphan")
    finance = relationship("LegFinance", back_populates="leg", uselist=False, cascade="all, delete-orphan")
    kpi = relationship("LegKPI", back_populates="leg", uselist=False, cascade="all, delete-orphan")

    @property
    def letter(self):
        """Convert sequence number to letter: 1->A, 2->B, etc."""
        return chr(64 + self.sequence) if self.sequence else "?"

    def generate_leg_code(self, vessel_code: int, dep_country: str, arr_country: str):
        """
        Generate leg code: SHIPCODE + LETTER + DEP_COUNTRY + ARR_COUNTRY + YEAR_LAST_DIGIT.
        Example: 1CFRBR6 = Anemos, 3rd call, France->Brazil, 2026
        """
        year_suffix = str(self.year)[-1] if self.year else "0"
        letter = self.letter
        return f"{vessel_code}{letter}{dep_country.upper()}{arr_country.upper()}{year_suffix}"

    def compute_navigation(self):
        """Compute distance and duration from navigation parameters."""
        if self.distance_nm and self.elongation_coeff:
            self.computed_distance = round(self.distance_nm * self.elongation_coeff, 1)
        if self.computed_distance and self.speed_knots and self.speed_knots > 0:
            self.estimated_duration_hours = round(self.computed_distance / self.speed_knots, 1)

    def __repr__(self):
        return f"<Leg {self.leg_code}>"
