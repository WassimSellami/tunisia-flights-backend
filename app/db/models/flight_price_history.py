from sqlalchemy import Column, DateTime, Integer, Float, ForeignKey
from app.db.base import Base


class FlightPriceHistory(Base):
    __tablename__ = "flightPriceHistory"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    flightId = Column(Integer, ForeignKey("flights.id"), index=True, nullable=False)
    price = Column(Float, nullable=False)
    priceEur = Column(Float, nullable=False)
    timestamp = Column(DateTime, nullable=False)
