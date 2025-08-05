from sqlalchemy import Column, DateTime, Integer, String, Float, ForeignKey
from app.db.base import Base


class Flight(Base):
    __tablename__ = "flights"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    departureDate = Column(DateTime, index=True, nullable=False)
    price = Column(Float, nullable=False)
    priceEur = Column(Float, nullable=False)
    departureAirportCode = Column(
        String(10), ForeignKey("airports.code"), nullable=False
    )
    arrivalAirportCode = Column(String(10), ForeignKey("airports.code"), nullable=False)
    airlineCode = Column(String(10), ForeignKey("airlines.code"), nullable=False)
