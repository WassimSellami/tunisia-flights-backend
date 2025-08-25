from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db import models, schemas


def get_flight(db: Session, flight_id: int):
    return db.query(models.Flight).filter(models.Flight.id == flight_id).first()


from sqlalchemy import func


def get_flights_with_min_max(
    db: Session,
    departure_airport_codes=None,
    arrival_airport_codes=None,
    start_date=None,
    end_date=None,
    airline_codes=None,
):
    subq = (
        db.query(
            models.FlightPriceHistory.flightId.label("flight_id"),
            func.min(models.FlightPriceHistory.priceEur).label("min_price"),
            func.max(models.FlightPriceHistory.priceEur).label("max_price"),
        )
        .group_by(models.FlightPriceHistory.flightId)
        .subquery()
    )

    q = db.query(models.Flight, subq.c.min_price, subq.c.max_price).outerjoin(
        subq, models.Flight.id == subq.c.flight_id
    )

    if departure_airport_codes:
        q = q.filter(models.Flight.departureAirportCode.in_(departure_airport_codes))
    if arrival_airport_codes:
        q = q.filter(models.Flight.arrivalAirportCode.in_(arrival_airport_codes))
    if start_date:
        q = q.filter(models.Flight.departureDate >= start_date)
    if end_date:
        q = q.filter(models.Flight.departureDate <= end_date)
    if airline_codes:
        q = q.filter(models.Flight.airlineCode.in_(airline_codes))

    return q.all()


def create_flight(db: Session, flight: schemas.FlightCreate) -> models.Flight:
    db_flight: models.Flight = models.Flight(**flight.model_dump())
    db.add(db_flight)
    db.commit()
    db.refresh(db_flight)
    return db_flight


def update_flight(db: Session, flight_id: int, flight_update: schemas.FlightUpdate):
    db_flight = get_flight(db, flight_id)
    if not db_flight:
        return None
    update_data = flight_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_flight, key, value)
    db.commit()
    db.refresh(db_flight)
    return db_flight


def delete_flight(db: Session, flight_id: int):
    db_flight = get_flight(db, flight_id)
    if not db_flight:
        return None
    db.delete(db_flight)
    db.commit()
    return db_flight
