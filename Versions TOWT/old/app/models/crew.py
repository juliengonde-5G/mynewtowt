from datetime import date as _date
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean, Date, func
)
from sqlalchemy.orm import relationship
from app.database import Base


class CrewMember(Base):
    __tablename__ = "crew_members"

    id = Column(Integer, primary_key=True, autoincrement=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    role = Column(String(50), nullable=False)  # capitaine, second, chef_mecanicien, cook, lieutenant, bosco, marin, eleve_officier
    phone = Column(String(50), nullable=True)
    email = Column(String(200), nullable=True)
    is_active = Column(Boolean, default=True)
    is_foreign = Column(Boolean, default=False)  # Personnel étranger
    # Border police / immigration fields
    nationality = Column(String(100), nullable=True)
    passport_number = Column(String(50), nullable=True)
    passport_expiry = Column(Date, nullable=True)
    visa_type = Column(String(50), nullable=True)  # schengen, work, transit, none
    visa_expiry = Column(Date, nullable=True)
    schengen_status = Column(String(20), nullable=True)  # compliant, warning, non_compliant
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    assignments = relationship("CrewAssignment", back_populates="member", cascade="all, delete-orphan")

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def role_label(self):
        labels = {
            "capitaine": "Capitaine",
            "second": "Second",
            "chef_mecanicien": "Chef mécanicien",
            "cook": "Cook",
            "lieutenant": "Lieutenant",
            "bosco": "Bosco",
            "marin": "Marin",
            "eleve_officier": "Élève Officier",
        }
        return labels.get(self.role, self.role)

    @property
    def passport_days_remaining(self):
        if not self.passport_expiry:
            return None
        return (self.passport_expiry - _date.today()).days

    @property
    def visa_days_remaining(self):
        if not self.visa_expiry:
            return None
        return (self.visa_expiry - _date.today()).days

    @property
    def compliance_status(self):
        """Return 'ok', 'warning' (< 30 days), or 'expired'."""
        issues = []
        for label, days in [("passport", self.passport_days_remaining), ("visa", self.visa_days_remaining)]:
            if days is not None:
                if days < 0:
                    return "expired"
                if days < 30:
                    issues.append(label)
        return "warning" if issues else "ok"

    def __repr__(self):
        return f"<CrewMember {self.full_name} ({self.role})>"


class CrewAssignment(Base):
    """Période d'embarquement d'un membre d'équipage sur un navire."""
    __tablename__ = "crew_assignments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    member_id = Column(Integer, ForeignKey("crew_members.id"), nullable=False)
    vessel_id = Column(Integer, ForeignKey("vessels.id"), nullable=False)
    embark_date = Column(Date, nullable=False)
    disembark_date = Column(Date, nullable=True)  # None = still on board
    embark_leg_id = Column(Integer, ForeignKey("legs.id"), nullable=True)  # Leg of embarkation
    disembark_leg_id = Column(Integer, ForeignKey("legs.id"), nullable=True)  # Leg of disembarkation
    status = Column(String(20), default="active")  # active, completed, planned
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    member = relationship("CrewMember", back_populates="assignments")
    vessel = relationship("Vessel")
    embark_leg = relationship("Leg", foreign_keys=[embark_leg_id])
    disembark_leg = relationship("Leg", foreign_keys=[disembark_leg_id])


class CrewTicket(Base):
    """Billet de transport pour un membre d'équipage embarquant/débarquant."""
    __tablename__ = "crew_tickets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    member_id = Column(Integer, ForeignKey("crew_members.id"), nullable=False)
    leg_id = Column(Integer, ForeignKey("legs.id"), nullable=False)
    ticket_type = Column(String(20), nullable=False)  # embarquement, debarquement
    transport_mode = Column(String(50), nullable=False)  # train, avion, bus, voiture, autre
    ticket_date = Column(Date, nullable=False)
    ticket_reference = Column(String(200), nullable=True)  # Numéro de billet
    filename = Column(String(255), nullable=True)
    file_path = Column(String(500), nullable=True)
    file_size = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    created_by = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    member = relationship("CrewMember")
    leg = relationship("Leg")


TRANSPORT_MODES = [
    {"value": "train", "label": "Train"},
    {"value": "avion", "label": "Avion"},
    {"value": "bus", "label": "Bus"},
    {"value": "voiture", "label": "Voiture"},
    {"value": "covoiturage", "label": "Covoiturage"},
    {"value": "autre", "label": "Autre"},
]


CREW_ROLES = [
    {"value": "capitaine", "label": "Capitaine"},
    {"value": "second", "label": "Second"},
    {"value": "chef_mecanicien", "label": "Chef mécanicien"},
    {"value": "cook", "label": "Cook"},
    {"value": "lieutenant", "label": "Lieutenant"},
    {"value": "bosco", "label": "Bosco"},
    {"value": "marin", "label": "Marin"},
    {"value": "eleve_officier", "label": "Élève Officier"},
]

REQUIRED_ROLES = ["capitaine", "second", "chef_mecanicien", "cook", "lieutenant", "bosco"]
