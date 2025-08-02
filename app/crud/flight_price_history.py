from sqlalchemy import func
from sqlalchemy.orm import Session
from app.db import models, schemas


def get_price_history(db: Session, flight_id: int):
    return (
        db.query(models.FlightPriceHistory)
        .filter(models.FlightPriceHistory.flightId == flight_id)
        .order_by(models.FlightPriceHistory.timestamp.desc())
        .all()
    )


def get_min_max_price_for_flight(
    db: Session, flight_id: int
) -> schemas.FlightMinMaxPrice:
    min_price = (
        db.query(func.min(models.FlightPriceHistory.price))
        .filter(models.FlightPriceHistory.flightId == flight_id)
        .scalar()
    )
    max_price = (
        db.query(func.max(models.FlightPriceHistory.price))
        .filter(models.FlightPriceHistory.flightId == flight_id)
        .scalar()
    )
    return schemas.FlightMinMaxPrice(
        flightId=flight_id, minPrice=min_price, maxPrice=max_price
    )


def create_price_history(db: Session, price_history: schemas.FlightPriceHistoryCreate):
    db_record = models.FlightPriceHistory(**price_history.dict())
    db.add(db_record)
    db.commit()
    db.refresh(db_record)
    return db_record


def get_price_history_by_id(db: Session, record_id: int):
    return (
        db.query(models.FlightPriceHistory)
        .filter(models.FlightPriceHistory.id == record_id)
        .first()
    )


def delete_price_history(db: Session, record_id: int):
    record = get_price_history_by_id(db, record_id)
    if not record:
        return None
    db.delete(record)
    db.commit()
    return record
