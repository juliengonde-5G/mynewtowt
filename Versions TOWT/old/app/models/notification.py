"""Notification model for dashboard alerts."""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import relationship
from app.database import Base


NOTIFICATION_TYPES = [
    ("new_order", "Nouvelle commande client"),
    ("new_cargo_message", "Nouveau message messagerie client"),
    ("eosp", "EOSP (End of Sea Passage)"),
    ("sosp", "SOSP (Start of Sea Passage)"),
    ("new_claim", "Nouveau claim ouvert"),
    ("eta_shift", "Décalage ETA signalé par le commandant"),
]

NOTIFICATION_ICONS = {
    "new_order": "📦",
    "new_cargo_message": "💬",
    "eosp": "⚓",
    "sosp": "⛵",
    "new_claim": "⚠️",
    "eta_shift": "🕐",
}


class Notification(Base):
    """Dashboard notification."""
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(String(50), nullable=False)  # from NOTIFICATION_TYPES
    title = Column(String(300), nullable=False)
    detail = Column(Text, nullable=True)
    link = Column(String(500), nullable=True)  # URL to navigate to
    is_read = Column(Boolean, default=False)
    is_archived = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Optional references
    leg_id = Column(Integer, ForeignKey("legs.id", ondelete="SET NULL"), nullable=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="SET NULL"), nullable=True)
    packing_list_id = Column(Integer, ForeignKey("packing_lists.id", ondelete="SET NULL"), nullable=True)

    leg = relationship("Leg", lazy="selectin")

    @property
    def icon(self):
        return NOTIFICATION_ICONS.get(self.type, "🔔")

    @property
    def type_label(self):
        for code, label in NOTIFICATION_TYPES:
            if code == self.type:
                return label
        return self.type
