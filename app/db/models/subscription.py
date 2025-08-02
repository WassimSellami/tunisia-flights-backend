from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from app.db.base import Base


class Subscription(Base):
    __tablename__ = "subscriptions"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    flightId = Column(Integer, ForeignKey("flights.id"), index=True, nullable=False)
    targetPrice = Column(Integer, nullable=False)
    isActive = Column(Boolean, default=True, nullable=False)
    email = Column(String(100), ForeignKey("users.email"), nullable=False, index=True)
