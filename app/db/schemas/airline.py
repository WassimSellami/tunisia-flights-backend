from pydantic import BaseModel


class AirlineBase(BaseModel):
    code: str
    name: str

    class Config:
        from_attributes = True


class AirlineCreate(AirlineBase):
    pass


class AirlineUpdate(BaseModel):
    name: str


class AirlineOut(AirlineBase):
    pass
