from sqlalchemy.orm import Session
from app.db import models, schemas


def get_airline(db: Session, code: str):
    return db.query(models.Airline).filter(models.Airline.code == code).first()


def get_airlines(db: Session):
    return db.query(models.Airline).all()


def create_airline(db: Session, airline: schemas.AirlineCreate):
    db_airline = models.Airline(**airline.dict())
    db.add(db_airline)
    db.commit()
    db.refresh(db_airline)
    return db_airline


def update_airline(db: Session, code: str, airline_update: schemas.AirlineUpdate):
    db_airline = get_airline(db, code)
    if not db_airline:
        return None
    for key, value in airline_update.dict(exclude_unset=True).items():
        setattr(db_airline, key, value)
    db.commit()
    db.refresh(db_airline)
    return db_airline


def delete_airline(db: Session, code: str):
    db_airline = get_airline(db, code)
    if not db_airline:
        return None
    db.delete(db_airline)
    db.commit()
    return db_airline
