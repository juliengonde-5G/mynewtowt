from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, func
from sqlalchemy.orm import relationship
from app.database import Base


class Vessel(Base):
    __tablename__ = "vessels"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(Integer, unique=True, nullable=False)  # 1=Anemos, 2=Artemis, 3=Atlantis, 4=Atlas
    name = Column(String(50), unique=True, nullable=False)
    imo_number = Column(String(20), nullable=True)
    flag = Column(String(50), nullable=True)
    dwt = Column(Float, nullable=True)  # Deadweight tonnage
    capacity_palettes = Column(Integer, nullable=True)  # Max palette capacity
    default_speed = Column(Float, default=8.0)  # Default exploitation speed in knots
    default_elongation = Column(Float, default=1.25)  # Default elongation coefficient
    opex_daily_sea = Column(Float, nullable=True)  # OPEX journalier en mer (€/jour)
    max_palettes = Column(Integer, default=850)  # Capacité max palettes
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    legs = relationship("Leg", back_populates="vessel", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Vessel {self.code} - {self.name}>"
