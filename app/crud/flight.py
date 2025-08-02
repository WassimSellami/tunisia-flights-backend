from sqlalchemy.orm import Session
from sqlalchemy import cast, Date
from typing import List, Optional
from datetime import date

from app.db import models, schemas


def get_flight(db: Session, flight_id: int):
    return db.query(models.Flight).filter(models.Flight.id == flight_id).first()


def get_flights(
    db: Session,
    departure_airport_codes: Optional[List[str]] = None,
    arrival_airport_codes: Optional[List[str]] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    airline_codes: Optional[List[str]] = None,
):
    query = db.query(models.Flight)

    if departure_airport_codes:
        query = query.filter(
            models.Flight.departureAirportCode.in_(departure_airport_codes)
        )
    if arrival_airport_codes:
        query = query.filter(
            models.Flight.arrivalAirportCode.in_(arrival_airport_codes)
        )
    if airline_codes:
        query = query.filter(models.Flight.airlineCode.in_(airline_codes))

    if start_date:
        query = query.filter(cast(models.Flight.departureDate, Date) >= start_date)
    if end_date:
        query = query.filter(cast(models.Flight.departureDate, Date) <= end_date)

    return query.all()


def create_flight(db: Session, flight: schemas.FlightCreate) -> models.Flight:
    db_flight: models.Flight = models.Flight(**flight.dict())
    db.add(db_flight)
    db.commit()
    db.refresh(db_flight)
    return db_flight


def update_flight(db: Session, flight_id: int, flight_update: schemas.FlightUpdate):
    db_flight = get_flight(db, flight_id)
    if not db_flight:
        return None
    update_data = flight_update.dict(exclude_unset=True)
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
