from sqlalchemy import Column, Integer, String, Boolean
from app.db.base import Base


class User(Base):
    __tablename__ = "users"
    email = Column(String(100), primary_key=True, index=True, nullable=False)
    enableNotificationsSetting = Column(Boolean, default=True, nullable=False)
