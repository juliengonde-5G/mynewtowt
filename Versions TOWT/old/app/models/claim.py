"""
Claims module models.

Claim = incident déclaré à l'assureur, lié à un navire et un leg.
Types: cargo (P&I), crew (P&I), hull (Hull/DIV/War Risk).
"""
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean, Date, Numeric, func
)
from sqlalchemy.orm import relationship
from app.database import Base


# ─── CONSTANTS ────────────────────────────────────────────────

CLAIM_TYPES = [
    ("cargo", "Cargo"),
    ("crew", "Crew"),
    ("hull", "Hull"),
]

CLAIM_STATUSES = [
    ("open", "Ouvert"),
    ("declared", "Déclaré assureur"),
    ("instruction", "En instruction"),
    ("accepted", "Accepté"),
    ("refused", "Refusé"),
    ("closed", "Clôturé"),
]

CLAIM_GUARANTEES = [
    ("pi", "P&I"),
    ("hull_div", "Hull — DIV"),
    ("war_risk", "War Risk"),
]

CLAIM_CONTEXTS = [
    ("loading", "Au chargement"),
    ("navigation", "Pendant la navigation"),
    ("unloading", "Au déchargement"),
    ("quay", "À quai"),
]

CLAIM_DOC_TYPES = [
    ("photo", "Photo / Constat visuel"),
    ("survey", "Rapport d'expertise / Survey"),
    ("correspondence", "Correspondance assureur"),
    ("invoice", "Facture / Devis réparation"),
    ("other", "Autre document"),
]

CLAIM_RESPONSIBILITY = [
    ("company", "Responsabilité compagnie"),
    ("third_party", "Responsabilité tiers"),
    ("pending", "En cours de détermination"),
    ("none", "Aucune responsabilité"),
]

TIMELINE_ACTION_TYPES = [
    ("status_change", "Changement de statut"),
    ("declaration", "Déclaration assureur"),
    ("expertise", "Expertise / Survey"),
    ("correspondence_in", "Courrier reçu assureur"),
    ("correspondence_out", "Courrier envoyé assureur"),
    ("document_added", "Document ajouté"),
    ("financial_update", "Mise à jour financière"),
    ("note", "Note interne"),
    ("client_exchange", "Échange client"),
]


# ─── MODELS ───────────────────────────────────────────────────

class Claim(Base):
    """Main claim record."""
    __tablename__ = "claims"

    id = Column(Integer, primary_key=True, autoincrement=True)
    reference = Column(String(30), unique=True, nullable=False, index=True)
    claim_type = Column(String(20), nullable=False)  # cargo, crew, hull
    status = Column(String(20), nullable=False, default="open")

    # Links
    vessel_id = Column(Integer, ForeignKey("vessels.id"), nullable=False)
    leg_id = Column(Integer, ForeignKey("legs.id"), nullable=False)

    # Cargo-specific: linked to order assignment
    order_assignment_id = Column(Integer, ForeignKey("order_assignments.id"), nullable=True)

    # Crew-specific: linked to crew member
    crew_member_id = Column(Integer, ForeignKey("crew_members.id"), nullable=True)

    # Context
    context = Column(String(30), nullable=True)  # loading, navigation, unloading, quay
    incident_date = Column(DateTime(timezone=True), nullable=True)
    incident_location = Column(String(200), nullable=True)
    description = Column(Text, nullable=False)

    # Cargo stowage position (auto-populated from stowage plan for cargo claims)
    cargo_zone = Column(String(20), nullable=True)  # e.g. "INF_AR_MIL"

    # Guarantee
    guarantee_type = Column(String(20), nullable=True)  # pi, hull_div, war_risk
    responsibility = Column(String(20), default="pending")  # company, third_party, pending, none

    # Financial
    provision_amount = Column(Numeric(12, 2), nullable=True)  # Estimated amount at opening
    franchise_amount = Column(Numeric(12, 2), nullable=True)  # Deductible
    indemnity_amount = Column(Numeric(12, 2), nullable=True)  # Amount paid by insurer
    company_charge = Column(Numeric(12, 2), nullable=True)    # Rest à charge compagnie

    currency = Column(String(3), default="EUR")

    # SOF link
    sof_event_id = Column(Integer, ForeignKey("sof_events.id"), nullable=True)

    # Meta
    declared_by = Column(String(200), nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    vessel = relationship("Vessel")
    leg = relationship("Leg")
    order_assignment = relationship("OrderAssignment")
    crew_member = relationship("CrewMember")
    sof_event = relationship("SofEvent")
    documents = relationship("ClaimDocument", back_populates="claim", cascade="all, delete-orphan")
    timeline = relationship("ClaimTimeline", back_populates="claim", cascade="all, delete-orphan",
                            order_by="ClaimTimeline.created_at.desc()")

    @property
    def type_label(self):
        return dict(CLAIM_TYPES).get(self.claim_type, self.claim_type)

    @property
    def status_label(self):
        return dict(CLAIM_STATUSES).get(self.status, self.status)

    @property
    def guarantee_label(self):
        return dict(CLAIM_GUARANTEES).get(self.guarantee_type, self.guarantee_type or "—")

    @property
    def responsibility_label(self):
        return dict(CLAIM_RESPONSIBILITY).get(self.responsibility, self.responsibility)

    @property
    def context_label(self):
        return dict(CLAIM_CONTEXTS).get(self.context, self.context or "—")

    def __repr__(self):
        return f"<Claim {self.reference} ({self.claim_type}/{self.status})>"


class ClaimDocument(Base):
    """Document attached to a claim as evidence."""
    __tablename__ = "claim_documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    claim_id = Column(Integer, ForeignKey("claims.id", ondelete="CASCADE"), nullable=False)
    doc_type = Column(String(30), nullable=False)  # photo, survey, correspondence, invoice, other
    title = Column(String(300), nullable=False)
    filename = Column(String(300), nullable=True)
    file_path = Column(String(500), nullable=True)
    notes = Column(Text, nullable=True)
    uploaded_by = Column(String(200), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    claim = relationship("Claim", back_populates="documents")

    @property
    def doc_type_label(self):
        return dict(CLAIM_DOC_TYPES).get(self.doc_type, self.doc_type)


class ClaimTimeline(Base):
    """Timeline entry: combines predefined actions + free comments."""
    __tablename__ = "claim_timeline"

    id = Column(Integer, primary_key=True, autoincrement=True)
    claim_id = Column(Integer, ForeignKey("claims.id", ondelete="CASCADE"), nullable=False)
    action_type = Column(String(30), nullable=False)  # status_change, declaration, expertise, etc.
    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)
    # For status changes
    old_value = Column(String(100), nullable=True)
    new_value = Column(String(100), nullable=True)
    # Attachment
    filename = Column(String(300), nullable=True)
    file_path = Column(String(500), nullable=True)
    # Who / when
    actor = Column(String(200), nullable=False)
    action_date = Column(DateTime(timezone=True), nullable=True)  # Date of the actual action
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    claim = relationship("Claim", back_populates="timeline")

    @property
    def action_type_label(self):
        return dict(TIMELINE_ACTION_TYPES).get(self.action_type, self.action_type)
