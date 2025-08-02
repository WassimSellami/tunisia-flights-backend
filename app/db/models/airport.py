from sqlalchemy import Column, String
from app.db.base import Base

class Airport(Base):
    __tablename__ = "airports"
    code = Column(String(10), primary_key=True)
    name = Column(String(20), nullable=False)
    country = Column(String(10), nullable=False)
