"""
Portal messaging model — threaded conversations between client and company
on the cargo client portal.
"""
from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey, Text, Boolean, func
)
from sqlalchemy.orm import relationship
from app.database import Base


class PortalMessage(Base):
    """A single message in a portal conversation thread."""
    __tablename__ = "portal_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    packing_list_id = Column(Integer, ForeignKey("packing_lists.id", ondelete="CASCADE"), nullable=False)

    sender_type = Column(String(20), nullable=False)  # "client" or "company"
    sender_name = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    packing_list = relationship("PackingList", backref="messages", foreign_keys=[packing_list_id])
