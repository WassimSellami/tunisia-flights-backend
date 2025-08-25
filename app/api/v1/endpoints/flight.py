from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date

from app.db import schemas, models
from app.crud import flight
from app.db.session import SessionLocal
from app.services import booking_url_service


router = APIRouter(prefix="/flights", tags=["flights"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def add_booking_url_to_flight(db_flight: models.Flight) -> str | None:
    flight_out = schemas.FlightOut.model_validate(db_flight)
    return booking_url_service.generate_booking_url(db_flight)


@router.get("/", response_model=List[schemas.FlightOut])
def read_flights(
    db: Session = Depends(get_db),
    departureAirportCodes: Optional[List[str]] = Query(None),
    arrivalAirportCodes: Optional[List[str]] = Query(None),
    startDate: Optional[date] = Query(None),
    endDate: Optional[date] = Query(None),
    airlineCodes: Optional[List[str]] = Query(None),
):
    db_flights = flight.get_flights_with_min_max(
        db,
        departure_airport_codes=departureAirportCodes,
        arrival_airport_codes=arrivalAirportCodes,
        start_date=startDate,
        end_date=endDate,
        airline_codes=airlineCodes,
    )

    return [
        schemas.FlightOut(
            **schemas.FlightOut.from_orm(flight).dict(),
            minPrice=min_price,
            maxPrice=max_price,
            bookingUrl=add_booking_url_to_flight(flight),
        )
        for flight, min_price, max_price in db_flights
    ]


@router.get("/{flight_id}", response_model=schemas.FlightOut)
def read_flight(flight_id: int, db: Session = Depends(get_db)):
    db_flight = flight.get_flight(db, flight_id)
    if not db_flight:
        raise HTTPException(status_code=404, detail="Flight not found")
    return add_booking_url_to_flight(db_flight)


@router.post("/", response_model=schemas.FlightOut)
def create_flight(flight_data: schemas.FlightCreate, db: Session = Depends(get_db)):
    return flight.create_flight(db, flight=flight_data)


@router.put("/{flight_id}", response_model=schemas.FlightOut)
def update_flight(
    flight_id: int,
    flight_update: schemas.FlightUpdate,
    db: Session = Depends(get_db),
):
    updated = flight.update_flight(db, flight_id, flight_update)
    if not updated:
        raise HTTPException(status_code=404, detail="Flight not found")
    return updated


@router.delete("/{flight_id}", response_model=schemas.FlightOut)
def delete_flight(flight_id: int, db: Session = Depends(get_db)):
    deleted = flight.delete_flight(db, flight_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Flight not found")
    return deleted
