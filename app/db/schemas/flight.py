from typing import Optional
from pydantic import BaseModel
from datetime import datetime


class FlightBase(BaseModel):
    departureDate: datetime
    price: int
    departureAirportCode: str
    arrivalAirportCode: str
    airlineCode: str


class FlightCreate(FlightBase):
    pass


class FlightUpdate(BaseModel):
    departureDate: datetime | None = None
    price: int | None = None
    departureAirportCode: str | None = None
    arrivalAirportCode: str | None = None
    airlineCode: str | None = None


class FlightOut(FlightBase):
    id: int
    bookingUrl: Optional[str] = None

    class Config:
        from_attributes = True
