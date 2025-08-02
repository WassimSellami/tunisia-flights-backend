from fastapi import APIRouter, Depends, HTTPException  # type: ignore
from sqlalchemy.orm import Session
from typing import List

from app.db import schemas
from app.crud import airport
from app.db.session import SessionLocal

router = APIRouter(prefix="/airports", tags=["airports"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/", response_model=List[schemas.AirportOut])
def read_airports(db: Session = Depends(get_db)):
    return airport.get_airports(db)


@router.get("/{code}", response_model=schemas.AirportOut)
def read_airport(code: str, db: Session = Depends(get_db)):
    db_airport = airport.get_airport(db, code)
    if not db_airport:
        raise HTTPException(status_code=404, detail="Airport not found")
    return db_airport


@router.post("/", response_model=schemas.AirportOut)
def create_airport(airport_in: schemas.AirportCreate, db: Session = Depends(get_db)):
    return airport.create_airport(db, airport_in)


@router.put("/{code}", response_model=schemas.AirportOut)
def update_airport(
    code: str, airport_in: schemas.AirportCreate, db: Session = Depends(get_db)
):
    updated = airport.update_airport(db, code, airport_in)
    if not updated:
        raise HTTPException(status_code=404, detail="Airport not found")
    return updated


@router.delete("/{code}", response_model=schemas.AirportOut)
def delete_airport(code: str, db: Session = Depends(get_db)):
    deleted = airport.delete_airport(db, code)
    if not deleted:
        raise HTTPException(status_code=404, detail="Airport not found")
    return deleted
