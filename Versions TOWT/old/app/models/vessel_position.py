"""Vessel position tracking — stores GPS points from satcom CSV files."""
from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, func, Index, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base


class VesselPosition(Base):
    __tablename__ = "vessel_positions"

    id = Column(Integer, primary_key=True, autoincrement=True)

    vessel_id = Column(Integer, ForeignKey("vessels.id", ondelete="CASCADE"), nullable=False, index=True)
    leg_id = Column(Integer, ForeignKey("legs.id", ondelete="SET NULL"), nullable=True, index=True)

    # Position
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)

    # Navigation
    sog = Column(Float, nullable=True)          # Speed Over Ground (knots)
    cog = Column(Float, nullable=True)          # Course Over Ground (degrees)

    # Metadata
    recorded_at = Column(DateTime(timezone=True), nullable=False, index=True)  # from CSV "Date" column
    source = Column(String(100), nullable=True)    # e.g. "Starlink_1921681001"
    import_batch = Column(String(100), nullable=True)  # filename of the imported CSV

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Prevent duplicate points (same vessel + same timestamp)
    __table_args__ = (
        UniqueConstraint("vessel_id", "recorded_at", name="uq_vessel_position_time"),
        Index("idx_vp_vessel_time", "vessel_id", "recorded_at"),
        Index("idx_vp_leg", "leg_id"),
    )

    # Relationships
    vessel = relationship("Vessel", lazy="joined")
    leg = relationship("Leg", lazy="joined")

    def __repr__(self):
        return f"<VesselPosition {self.vessel_id} {self.recorded_at} ({self.latitude},{self.longitude})>"
