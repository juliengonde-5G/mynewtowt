"""Models for On Board module: SOF events, notifications, cargo documents, ETA shifts."""
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean, Date, func
)
from sqlalchemy.orm import relationship
from app.database import Base


# ─── ETA SHIFT REASONS ────────────────────────────────────────
ETA_SHIFT_REASONS = [
    ("weather", "Conditions météo / Weather conditions"),
    ("mechanical", "Problème mécanique / Mechanical issue"),
    ("port_congestion", "Congestion portuaire / Port congestion"),
    ("cargo_ops", "Opérations cargo prolongées / Extended cargo ops"),
    ("crew", "Raison liée à l'équipage / Crew-related"),
    ("routing", "Changement de route / Routing change"),
    ("speed_adjustment", "Ajustement de vitesse / Speed adjustment"),
    ("port_stay_change", "Durée d'escale modifiée / Port stay change"),
    ("other", "Autre / Other"),
]


class ETAShift(Base):
    """Records every ETA/ETD modification with justification and full history."""
    __tablename__ = "eta_shifts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    leg_id = Column(Integer, ForeignKey("legs.id", ondelete="CASCADE"), nullable=False)
    vessel_id = Column(Integer, ForeignKey("vessels.id", ondelete="CASCADE"), nullable=False)

    # What changed
    field_changed = Column(String(10), nullable=False)  # "eta" or "etd"
    old_value = Column(DateTime(timezone=True), nullable=True)
    new_value = Column(DateTime(timezone=True), nullable=True)
    shift_hours = Column(Float, nullable=False)  # positive = delay, negative = advance

    # Justification (mandatory)
    reason = Column(String(50), nullable=False)  # code from ETA_SHIFT_REASONS
    justification = Column(Text, nullable=False)  # free text detail

    # Who and when
    created_by = Column(String(200), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Snapshot of cascading impact
    legs_affected = Column(Integer, default=0)  # number of downstream legs recalculated

    leg = relationship("Leg", backref="eta_shifts")
    vessel = relationship("Vessel")


# ─── SOF EVENT TYPES ────────────────────────────────────────
SOF_EVENT_TYPES = [
    ("EOSP", "EOSP (End of Sea Passage)"),
    ("SOSP", "SOSP (Start of Sea Passage)"),
    ("FREE_PRATIQUE", "Free pratique granted"),
    ("NOR_RETENDERED", "Notice of Readiness RE-Tendered - Without prejudice"),
    ("PILOT_ONBOARD", "Pilot onboard"),
    ("PILOT_OFF", "Pilot off"),
    ("TUG_FAST", "Tug made fast / escorting"),
    ("TUG_CAST_OFF", "Tug cast off"),
    ("TUG_FREE", "Tug free"),
    ("FIRST_LINE", "First line ashore"),
    ("ALL_FAST", "All fast"),
    ("COMMENCE_UNMOORING", "Commence unmooring"),
    ("ALL_CLEAR", "All clear"),
    ("ANCHORED", "Anchored"),
    ("ANCHOR_AWEIGH", "Anchor aweigh"),
    ("GANGWAY_RIGGED", "Ship's / Shore gangway rigged"),
    ("HOLDS_INSPECTION", "Cargo holds inspection commenced / completed"),
    ("HATCH_OPEN_CLOSE", "FWD / Aft cargo hold hatch open / close"),
    ("COMMENCE_LOADING", "Commence loading / discharging"),
    ("COMPLETED_LOADING", "Completed loading / discharging"),
    ("LOADING_SUSPENDED", "Loading / Discharging suspended - Shore / Ship stop"),
    ("LOADING_RESUMED", "Loading / discharging resumed"),
    # ─── CLAIMS ───
    ("CLAIM_DECLARED", "Claim declared / Sinistre déclaré"),
    ("CLAIM_UPDATED", "Claim updated / Sinistre mis à jour"),
]

# ─── CARGO DOCUMENT TYPES ───────────────────────────────────
CARGO_DOC_TYPES = [
    ("SOF", "Statement of Facts"),
    ("NOR", "Notice of Readiness"),
    ("NOR_RT", "Notice of Readiness Re-Tendered"),
    ("HOLDS_CERT", "Holds Readiness Certificate"),
    ("KEY_MEETING", "Key Transfer Meeting"),
    ("PRE_MEETING", "Pre-Loading / Discharging Meeting"),
    ("LOP_FP", "Letter of Protest - Free Pratique"),
    ("LOP_DELAYS", "Letter of Protest - Delays & Restrictions"),
    ("LOP_DOCUMENT", "Letter of Protest - Documentation"),
    ("LOP_QTY", "Letter of Protest - Quantity"),
    ("LOP_DEADFREIGHT", "Letter of Protest - Deadfreight"),
    ("LOP_OTHER", "Letter of Protest - Other"),
    ("MATES_RECEIPT", "Mate's Receipt"),
]


class SofEvent(Base):
    """Statement of Facts - individual event record."""
    __tablename__ = "sof_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    leg_id = Column(Integer, ForeignKey("legs.id", ondelete="CASCADE"), nullable=False)
    event_type = Column(String(50), nullable=False)  # code from SOF_EVENT_TYPES
    event_label = Column(String(300), nullable=False)  # display text (can be customized)
    event_date = Column(Date, nullable=True)
    event_time = Column(String(10), nullable=True)  # HH:MM format
    event_time_tz = Column(String(50), nullable=True, default="UTC")  # IANA timezone of event_time
    remarks = Column(Text, nullable=True)
    created_by = Column(String(200), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    leg = relationship("Leg", backref="sof_events")


class OnboardNotification(Base):
    """Notification for onboard crew about changes to escale, crew, or cargo."""
    __tablename__ = "onboard_notifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    leg_id = Column(Integer, ForeignKey("legs.id", ondelete="CASCADE"), nullable=False)
    category = Column(String(30), nullable=False)  # crew, escale, cargo
    title = Column(String(300), nullable=False)
    detail = Column(Text, nullable=True)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    leg = relationship("Leg", backref="onboard_notifications")


class CargoDocument(Base):
    """Generated cargo document for a leg."""
    __tablename__ = "cargo_documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    leg_id = Column(Integer, ForeignKey("legs.id", ondelete="CASCADE"), nullable=False)
    doc_type = Column(String(30), nullable=False)  # code from CARGO_DOC_TYPES
    title = Column(String(300), nullable=False)
    data_json = Column(Text, nullable=True)  # JSON blob with form data
    created_by = Column(String(200), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    leg = relationship("Leg", backref="cargo_documents")


# ─── ATTACHMENT CATEGORIES ─────────────────────────────────────
ATTACHMENT_CATEGORIES = [
    ("photo", "Photo"),
    ("document", "Document"),
    ("report", "Rapport / Report"),
    ("certificate", "Certificat / Certificate"),
    ("port_agent", "Document agent d'escale / Port agent"),
    ("bl_signed", "BL signé / Signed BL"),
    ("letter_protest", "Lettre de protestation / Letter of Protest"),
    ("other", "Autre / Other"),
]


class CargoDocumentAttachment(Base):
    """File or photo attachment linked to a specific cargo document."""
    __tablename__ = "cargo_document_attachments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("cargo_documents.id", ondelete="CASCADE"), nullable=False)
    leg_id = Column(Integer, ForeignKey("legs.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(300), nullable=False)
    filename = Column(String(300), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=True)
    mime_type = Column(String(100), nullable=True)
    uploaded_by = Column(String(200), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    document = relationship("CargoDocument", backref="attachments")
    leg = relationship("Leg")


class OnboardAttachment(Base):
    """File or photo attachment for a leg (onboard module)."""
    __tablename__ = "onboard_attachments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    leg_id = Column(Integer, ForeignKey("legs.id", ondelete="CASCADE"), nullable=False)
    category = Column(String(30), nullable=False, default="document")  # from ATTACHMENT_CATEGORIES
    title = Column(String(300), nullable=False)
    filename = Column(String(300), nullable=False)  # original filename
    file_path = Column(String(500), nullable=False)  # server path
    file_size = Column(Integer, nullable=True)  # bytes
    mime_type = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    uploaded_by = Column(String(200), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    leg = relationship("Leg", backref="attachments")


# ─── ONBOARD CONVERSATION ──────────────────────────────────────
# Bot username used for system / automated messages (mentionable as @mytowt_bot)
MYTOWT_BOT_USERNAME = "mytowt_bot"
MYTOWT_BOT_NAME = "my_TOWT bot"


class OnboardMessage(Base):
    """Chat message in the onboard conversation between shore team and crew."""
    __tablename__ = "onboard_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    vessel_id = Column(Integer, ForeignKey("vessels.id", ondelete="CASCADE"), nullable=False)
    leg_id = Column(Integer, ForeignKey("legs.id", ondelete="CASCADE"), nullable=True)

    # Author — either a real user or the bot
    author_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    author_name = Column(String(200), nullable=False)  # display name (snapshot)
    author_username = Column(String(100), nullable=True)  # for @mention resolution
    is_bot = Column(Boolean, default=False, nullable=False)
    is_system = Column(Boolean, default=False, nullable=False)  # action notification

    # Content
    body = Column(Text, nullable=False)
    mentions = Column(String(500), nullable=True)  # comma-separated usernames mentioned

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    vessel = relationship("Vessel")
    leg = relationship("Leg")
    author = relationship("User")


class OnboardMessageMention(Base):
    """A user that was mentioned in a message — used for read/unread tracking."""
    __tablename__ = "onboard_message_mentions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    message_id = Column(Integer, ForeignKey("onboard_messages.id", ondelete="CASCADE"), nullable=False)
    username = Column(String(100), nullable=False)  # mentioned username (or 'mytowt_bot')
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    is_read = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    message = relationship("OnboardMessage", backref="mention_records")
