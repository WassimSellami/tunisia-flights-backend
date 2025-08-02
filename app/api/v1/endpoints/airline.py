from fastapi import APIRouter, Depends, HTTPException  # type: ignore
from sqlalchemy.orm import Session
from typing import List

from app.db import schemas
from app.crud import airline
from app.db.session import SessionLocal

router = APIRouter(prefix="/airlines", tags=["airlines"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/", response_model=List[schemas.AirlineOut])
def read_airlines(db: Session = Depends(get_db)):
    return airline.get_airlines(db)


@router.get("/{code}", response_model=schemas.AirlineOut)
def read_airline(code: str, db: Session = Depends(get_db)):
    db_airline = airline.get_airline(db, code=code)
    if not db_airline:
        raise HTTPException(status_code=404, detail="Airline not found")
    return db_airline


@router.post("/", response_model=schemas.AirlineOut)
def create_airline(airline_data: schemas.AirlineCreate, db: Session = Depends(get_db)):
    return airline.create_airline(db, airline=airline_data)


@router.put("/{code}", response_model=schemas.AirlineOut)
def update_airline(
    code: str, airline_update: schemas.AirlineUpdate, db: Session = Depends(get_db)
):
    updated = airline.update_airline(db, code, airline_update)
    if not updated:
        raise HTTPException(status_code=404, detail="Airline not found")
    return updated


@router.delete("/{code}", response_model=schemas.AirlineOut)
def delete_airline(code: str, db: Session = Depends(get_db)):
    deleted = airline.delete_airline(db, code)
    if not deleted:
        raise HTTPException(status_code=404, detail="Airline not found")
    return deleted
