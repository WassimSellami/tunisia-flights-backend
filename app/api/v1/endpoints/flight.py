from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date

from app.db import schemas, models
from app.crud import flight
from app.db.session import SessionLocal
from app.services import booking_url_service
from app.services import fetch_flights as scraped_data_service
from app.services import email_alerts


router = APIRouter(prefix="/flights", tags=["flights"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def add_booking_url_to_flight(db_flight: models.Flight) -> schemas.FlightOut:
    flight_out = schemas.FlightOut.model_validate(db_flight)
    flight_out.bookingUrl = booking_url_service.generate_booking_url(
        db_flight
    )
    return flight_out


@router.get("/", response_model=List[schemas.FlightOut])
def read_flights(
    db: Session = Depends(get_db),
    departureAirportCodes: Optional[List[str]] = Query(None),
    arrivalAirportCodes: Optional[List[str]] = Query(None),
    startDate: Optional[date] = Query(None),
    endDate: Optional[date] = Query(None),
    airlineCodes: Optional[List[str]] = Query(None),
):
    db_flights = flight.get_flights(
        db,
        departure_airport_codes=departureAirportCodes,
        arrival_airport_codes=arrivalAirportCodes,
        start_date=startDate,
        end_date=endDate,
        airline_codes=airlineCodes,
    )

    return [add_booking_url_to_flight(f) for f in db_flights]


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


@router.post("/report-scraped-data", status_code=202) # 202 Accepted
def report_scraped_data(
    payload: schemas.ScrapedDataPayload,
    db: Session = Depends(get_db)
):
    """
    Receives a batch of scraped flight data from a scraper service.
    This endpoint processes the data, updates the database, and triggers alerts.
    """
    updated_flights = scraped_data_service.process_scraped_flights(db, payload)
    
    if updated_flights:
        # logger.info(f"Triggering price alerts for {len(updated_flights)} flights.")
        email_alerts.check_and_send_alerts_for_flights(db, updated_flights)
    
    return {
        "message": "Scraped data report accepted for processing."
    }