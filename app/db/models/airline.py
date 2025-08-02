from sqlalchemy import Column, String
from app.db.base import Base

class Airline(Base):
    __tablename__ = "airlines"
    code = Column(String(10), primary_key=True)
    name = Column(String(20), nullable=False)