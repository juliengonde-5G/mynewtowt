from sqlalchemy import Column, Integer, Float, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from app.database import Base


class LegKPI(Base):
    __tablename__ = "leg_kpis"

    id = Column(Integer, primary_key=True, autoincrement=True)
    leg_id = Column(Integer, ForeignKey("legs.id", ondelete="CASCADE"), nullable=False, unique=True)
    cargo_tons = Column(Float, default=0)  # Tonnes transportées (manual or from orders)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    leg = relationship("Leg", back_populates="kpi")
