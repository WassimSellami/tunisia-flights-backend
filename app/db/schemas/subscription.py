from pydantic import BaseModel, EmailStr
from typing import Optional


class SubscriptionBase(BaseModel):
    flightId: int
    email: EmailStr
    targetPrice: int

    class Config:
        from_attributes = True


class SubscriptionCreate(SubscriptionBase):
    isActive: Optional[bool] = True


class SubscriptionUpdate(BaseModel):
    flightId: Optional[int] = None
    email: Optional[EmailStr] = None
    targetPrice: Optional[int] = None
    isActive: Optional[bool] = None
    enableEmailNotifications: Optional[bool] = None


class SubscriptionOut(SubscriptionBase):
    id: int
    isActive: bool
