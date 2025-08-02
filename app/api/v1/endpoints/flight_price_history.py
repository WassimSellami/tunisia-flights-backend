from fastapi import APIRouter, Depends, HTTPException  # type: ignore
from sqlalchemy.orm import Session
from typing import List

from app.db import schemas
from app.crud import flight_price_history
from app.db.session import SessionLocal

router = APIRouter(prefix="/price-history", tags=["flight price history"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/flight/{flight_id}", response_model=List[schemas.FlightPriceHistoryOut])
def read_price_history(flight_id: int, db: Session = Depends(get_db)):
    return flight_price_history.get_price_history(db, flight_id)


@router.get("/{record_id}", response_model=schemas.FlightPriceHistoryOut)
def read_price_history_by_id(record_id: int, db: Session = Depends(get_db)):
    record = flight_price_history.get_price_history_by_id(db, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Price history record not found")
    return record


@router.get("/flight/{flight_id}/min-max", response_model=schemas.FlightMinMaxPrice)
def get_min_max_flight_price(flight_id: int, db: Session = Depends(get_db)):
    min_max_prices = flight_price_history.get_min_max_price_for_flight(db, flight_id)
    return min_max_prices


@router.post("/", response_model=schemas.FlightPriceHistoryOut)
def create_price_history(
    price: schemas.FlightPriceHistoryCreate, db: Session = Depends(get_db)
):
    return flight_price_history.create_price_history(db, price)


@router.delete("/{record_id}", response_model=schemas.FlightPriceHistoryOut)
def delete_price_history(record_id: int, db: Session = Depends(get_db)):
    deleted = flight_price_history.delete_price_history(db, record_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Price history record not found")
    return deleted
