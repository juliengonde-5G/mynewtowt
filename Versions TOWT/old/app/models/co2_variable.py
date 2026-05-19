from sqlalchemy import Column, Integer, String, Float, DateTime, Date, Boolean, func
from app.database import Base


class Co2Variable(Base):
    """CO2 decarbonation calculation variables with history tracking.

    Key variables:
    - towt_co2_ef: TOWT CO2 emission factor (gCO2/t.km) — historized
    - conventional_co2_ef: Conventional transport CO2 EF (gCO2/t.km)
    - sailing_cargo_capacity: Sailing cargo capacity (mt)
    - nm_to_km: Nautical miles to km conversion factor
    """
    __tablename__ = "co2_variables"

    id = Column(Integer, primary_key=True, autoincrement=True)
    variable_name = Column(String(100), nullable=False, index=True)
    variable_value = Column(Float, nullable=False)
    unit = Column(String(50), nullable=True)
    description = Column(String(255), nullable=True)
    effective_date = Column(Date, nullable=False)
    is_current = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<Co2Variable {self.variable_name}={self.variable_value} from {self.effective_date}>"


# Default values
CO2_DEFAULTS = {
    "towt_co2_ef": {"value": 1.5, "unit": "gCO2/t.km", "description": "TOWT CO2 emission factor"},
    "conventional_co2_ef": {"value": 13.7, "unit": "gCO2/t.km", "description": "Conventional transport CO2 emission factor"},
    "sailing_cargo_capacity": {"value": 1100, "unit": "mt", "description": "Sailing cargo capacity"},
    "nm_to_km": {"value": 1.852, "unit": "km/nm", "description": "Nautical miles to km conversion"},
}
