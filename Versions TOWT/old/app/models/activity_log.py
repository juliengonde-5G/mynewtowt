"""Activity Log model — tracks all user actions in the application."""
from sqlalchemy import Column, Integer, String, Text, DateTime, func, Index
from app.database import Base


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Who
    user_id = Column(Integer, nullable=True)  # nullable for failed logins
    user_name = Column(String(100), nullable=True)  # snapshot at log time
    user_role = Column(String(50), nullable=True)

    # What
    action = Column(String(20), nullable=False)  # login, logout, create, update, delete, login_fail
    module = Column(String(50), nullable=False)  # auth, commercial, cargo, crew, etc.
    entity_type = Column(String(50), nullable=True)  # order, leg, user, claim, etc.
    entity_id = Column(String(50), nullable=True)  # PK of the entity
    entity_label = Column(String(200), nullable=True)  # human-readable label (e.g. "ORD-2025-042")

    # Details
    detail = Column(Text, nullable=True)  # additional info (e.g. "status: draft → confirmed")
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6

    # When
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    __table_args__ = (
        Index("idx_activity_user", "user_id"),
        Index("idx_activity_action", "action"),
        Index("idx_activity_module", "module"),
        Index("idx_activity_created", "created_at"),
    )

    def __repr__(self):
        return f"<ActivityLog {self.action} {self.module}/{self.entity_type} by {self.user_name}>"
