from fastapi import (  # type: ignore
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db import schemas
from app.crud import user
from app.db.session import (
    SessionLocal,
)

router = APIRouter(prefix="/users", tags=["users"])


# Dependency to get a DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
def create_user_endpoint(user_data: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = user.get_user(db, email=user_data.email)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already registered",
        )
    return user.create_user(db, user=user_data)


@router.get("/", response_model=List[schemas.UserOut])
def read_users_endpoint(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    users = user.get_users(db, skip=skip, limit=limit)
    return users


@router.get("/{email}", response_model=schemas.UserOut)
def read_user_endpoint(email: str, db: Session = Depends(get_db)):
    db_user = user.get_user(db, email=email)
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return db_user


@router.put("/{email}", response_model=schemas.UserOut)
def update_user_endpoint(
    email: str,
    user_update: schemas.UserUpdate,
    db: Session = Depends(get_db),
):
    updated_user = user.update_user(db, email, user_update)
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return updated_user


@router.delete("/{email}", response_model=schemas.UserOut)
def delete_user_endpoint(email: str, db: Session = Depends(get_db)):
    deleted_user = user.delete_user(db, email)
    if not deleted_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return deleted_user
