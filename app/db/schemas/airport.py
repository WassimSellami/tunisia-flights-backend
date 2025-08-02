from pydantic import BaseModel
from datetime import datetime


class AirportBase(BaseModel):
    code: str
    name: str
    country: str

    class Config:
        from_attributes = True


class AirportCreate(AirportBase):
    pass


class AirportOut(AirportBase):
    pass
