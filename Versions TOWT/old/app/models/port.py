from sqlalchemy import Column, Integer, String, Float, Boolean
from app.database import Base


class Port(Base):
    __tablename__ = "ports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    locode = Column(String(5), unique=True, nullable=False, index=True)  # FRFEC, BRSSO...
    name = Column(String(200), nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    country_code = Column(String(2), nullable=False, index=True)
    zone_code = Column(String(20), nullable=True)
    is_shortcut = Column(Boolean, default=False)  # Quick access ports (Fécamp, São Sebastião)

    def __repr__(self):
        return f"<Port {self.locode} - {self.name}>"
