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
    min_price_eur, max_price_eur = (
        db.query(
            func.min(models.FlightPriceHistory.priceEur),
            func.max(models.FlightPriceHistory.priceEur),
        )
        .filter(models.FlightPriceHistory.flightId == flight_id)
        .one()
    )

    return schemas.FlightMinMaxPrice(
        flightId=flight_id, minPrice=min_price_eur, maxPrice=max_price_eur
    )


def create_price_history(db: Session, price_history: schemas.FlightPriceHistoryCreate):
    db_record = models.FlightPriceHistory(**price_history.model_dump())
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
