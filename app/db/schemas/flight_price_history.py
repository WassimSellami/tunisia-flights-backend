from typing import Optional
from pydantic import BaseModel
from datetime import datetime


class FlightPriceHistoryBase(BaseModel):
    flightId: int
    price: int
    timestamp: datetime

    class Config:
        from_attributes = True


class FlightPriceHistoryCreate(FlightPriceHistoryBase):
    pass


class FlightPriceHistoryOut(FlightPriceHistoryBase):
    id: int


class FlightMinMaxPrice(BaseModel):
    minPrice: Optional[int] = None
    maxPrice: Optional[int] = None
    flightId: int
