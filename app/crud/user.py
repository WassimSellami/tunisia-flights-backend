from sqlalchemy.orm import Session
from app.db import models, schemas
from typing import Optional, List


def get_user(db: Session, email: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.email == email).first()


def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[models.User]:
    return db.query(models.User).offset(skip).limit(limit).all()


def create_user(db: Session, user: schemas.UserCreate) -> models.User:
    db_user = models.User(
        email=user.email, enableNotificationsSetting=user.enableNotificationsSetting
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def update_user(
    db: Session, email: str, user_update: schemas.UserUpdate
) -> Optional[models.User]:
    db_user = get_user(db, email)
    if not db_user:
        return None

    update_data = user_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_user, key, value)

    db.commit()
    db.refresh(db_user)
    return db_user


def delete_user(db: Session, email: str) -> Optional[models.User]:
    db_user = get_user(db, email)
    if not db_user:
        return None
    db.delete(db_user)
    db.commit()
    return db_user
