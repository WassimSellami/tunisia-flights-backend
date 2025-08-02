from sqlalchemy.orm import Session
from app.db import models, schemas


def get_airport(db: Session, code: str):
    return db.query(models.Airport).filter(models.Airport.code == code).first()


def get_airports(db: Session):
    return db.query(models.Airport).all()


def create_airport(db: Session, airport: schemas.AirportCreate):
    db_airport = models.Airport(**airport.dict())
    db.add(db_airport)
    db.commit()
    db.refresh(db_airport)
    return db_airport


def update_airport(db: Session, code: str, airport: schemas.AirportCreate):
    db_airport = get_airport(db, code)
    if not db_airport:
        return None
    for key, value in airport.dict().items():
        setattr(db_airport, key, value)
    db.commit()
    db.refresh(db_airport)
    return db_airport


def delete_airport(db: Session, code: str):
    db_airport = get_airport(db, code)
    if not db_airport:
        return None
    db.delete(db_airport)
    db.commit()
    return db_airport
