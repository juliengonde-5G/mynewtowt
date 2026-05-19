"""
Portal access audit log — tracks every access to external portals.
RGPD compliance: who accessed what data and when.

Sprint 2 security hardening (A2.3): the raw token is no longer stored.
``token_hash`` holds sha256(token) so a DB leak does not expose the
portal access credentials.
"""
from sqlalchemy import Column, Integer, String, DateTime, func
from app.database import Base


class PortalAccessLog(Base):
    __tablename__ = "portal_access_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    portal_type = Column(String(20), nullable=False)  # "cargo", "planning"
    token_hash = Column(String(64), nullable=False, index=True)  # sha256 hex
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(500), nullable=True)
    path = Column(String(300), nullable=False)
    packing_list_id = Column(Integer, nullable=True)
    accessed_at = Column(DateTime(timezone=True), server_default=func.now())
