from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey, Text, Table, func
)
from sqlalchemy.orm import relationship
from app.database import Base


# Many-to-many: operations ↔ crew members (for embark/disembark)
operation_crew = Table(
    "operation_crew", Base.metadata,
    Column("operation_id", Integer, ForeignKey("escale_operations.id"), primary_key=True),
    Column("crew_member_id", Integer, ForeignKey("crew_members.id"), primary_key=True),
)


class EscaleOperation(Base):
    __tablename__ = "escale_operations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    leg_id = Column(Integer, ForeignKey("legs.id"), nullable=False)
    operation_type = Column(String(30), nullable=False)
    action = Column(String(50), nullable=False)
    planned_start = Column(DateTime(timezone=True), nullable=True)
    planned_end = Column(DateTime(timezone=True), nullable=True)
    planned_duration_hours = Column(Float, nullable=True)
    actual_start = Column(DateTime(timezone=True), nullable=True)
    actual_end = Column(DateTime(timezone=True), nullable=True)
    actual_duration_hours = Column(Float, nullable=True)
    intervenant = Column(String(200), nullable=True)
    description = Column(Text, nullable=True)

    # Cost
    cost_forecast = Column(Float, nullable=True)  # Coût prévisionnel
    cost_actual = Column(Float, nullable=True)     # Coût réalisé

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    leg = relationship("Leg", back_populates="operations")
    crew_members = relationship("CrewMember", secondary=operation_crew)


class DockerShift(Base):
    __tablename__ = "docker_shifts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    leg_id = Column(Integer, ForeignKey("legs.id"), nullable=False)
    hold = Column(String(10), nullable=False)
    planned_start = Column(DateTime(timezone=True), nullable=True)
    planned_end = Column(DateTime(timezone=True), nullable=True)
    actual_start = Column(DateTime(timezone=True), nullable=True)
    actual_end = Column(DateTime(timezone=True), nullable=True)
    planned_palettes = Column(Integer, nullable=True)
    actual_palettes = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)

    # Cost
    cost_forecast = Column(Float, nullable=True)
    cost_actual = Column(Float, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    leg = relationship("Leg", back_populates="docker_shifts")

    @property
    def planned_rate(self):
        if self.planned_palettes and self.planned_start and self.planned_end:
            hours = (self.planned_end - self.planned_start).total_seconds() / 3600
            return round(self.planned_palettes / hours, 1) if hours > 0 else 0
        return None

    @property
    def actual_rate(self):
        if self.actual_palettes and self.actual_start and self.actual_end:
            hours = (self.actual_end - self.actual_start).total_seconds() / 3600
            return round(self.actual_palettes / hours, 1) if hours > 0 else 0
        return None

    @property
    def rate_delta_pct(self):
        pr = self.planned_rate
        ar = self.actual_rate
        if pr and ar and pr > 0:
            return round(((ar - pr) / pr) * 100, 1)
        return None
