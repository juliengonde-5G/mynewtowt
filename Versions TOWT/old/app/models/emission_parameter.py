from sqlalchemy import Column, Integer, String, Float, DateTime, func
from app.database import Base


class EmissionParameter(Base):
    __tablename__ = "emission_parameters"

    id = Column(Integer, primary_key=True, autoincrement=True)
    parameter_name = Column(String(100), unique=True, nullable=False)
    parameter_value = Column(Float, nullable=False)
    unit = Column(String(50), nullable=True)
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
