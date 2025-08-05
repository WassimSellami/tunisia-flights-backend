from typing import Optional
from pydantic import BaseModel
from datetime import datetime


class FlightBase(BaseModel):
    departureDate: datetime
    price: float
    priceEur: float
    departureAirportCode: str
    arrivalAirportCode: str
    airlineCode: str


class FlightCreate(FlightBase):
    pass


class FlightUpdate(BaseModel):
    departureDate: datetime | None = None
    price: float | None = None
    priceEur: float | None = None
    departureAirportCode: str | None = None
    arrivalAirportCode: str | None = None
    airlineCode: str | None = None


class FlightOut(FlightBase):
    id: int
    bookingUrl: Optional[str] = None

    class Config:
        from_attributes = True
