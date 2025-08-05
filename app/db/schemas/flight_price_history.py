from typing import Optional
from pydantic import BaseModel
from datetime import datetime


class FlightPriceHistoryBase(BaseModel):
    flightId: int
    price: float
    priceEur: float
    timestamp: datetime

    class Config:
        from_attributes = True


class FlightPriceHistoryCreate(FlightPriceHistoryBase):
    pass


class FlightPriceHistoryOut(FlightPriceHistoryBase):
    id: int


class FlightMinMaxPrice(BaseModel):
    minPrice: Optional[float] = None
    maxPrice: Optional[float] = None
    flightId: int
