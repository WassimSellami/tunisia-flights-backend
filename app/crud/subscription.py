from sqlalchemy.orm import Session
from app.db import models, schemas
from typing import List, Optional


def get_subscriptions_by_email(db: Session, email: str) -> List[models.Subscription]:
    return (
        db.query(models.Subscription).filter(models.Subscription.email == email).all()
    )


def get_subscription_by_flight_and_email(
    db: Session, flight_id: int, email: str
) -> Optional[models.Subscription]:
    return (
        db.query(models.Subscription)
        .filter(models.Subscription.flightId == flight_id)
        .filter(models.Subscription.email == email)
        .first()
    )


def get_subscription(
    db: Session, subscription_id: int
) -> Optional[models.Subscription]:
    return (
        db.query(models.Subscription)
        .filter(models.Subscription.id == subscription_id)
        .first()
    )


def get_subscriptions(db: Session) -> List[models.Subscription]:
    return (
        db.query(models.Subscription).filter(models.Subscription.isActive == True).all()
    )


def get_active_subscriptions_for_flight_with_notifications_enabled(
    db: Session, flight_id: int
) -> List[models.Subscription]:
    """
    Retrieves active subscriptions for a given flight where the associated user
    has email notifications enabled.
    """
    return (
        db.query(models.Subscription)
        .join(models.User, models.Subscription.email == models.User.email)
        .filter(models.Subscription.flightId == flight_id)
        .filter(models.Subscription.isActive == True)
        .filter(models.User.enableNotificationsSetting == True)
        .all()
    )


def create_subscription(
    db: Session, subscription: schemas.SubscriptionCreate
) -> models.Subscription:
    db_subscription = models.Subscription(**subscription.model_dump())
    db_subscription.isActive = True  # type: ignore
    db.add(db_subscription)
    db.commit()
    db.refresh(db_subscription)
    return db_subscription


def update_subscription(
    db: Session, subscription_id: int, subscription_update: schemas.SubscriptionUpdate
) -> Optional[models.Subscription]:
    db_subscription = get_subscription(db, subscription_id)
    if not db_subscription:
        return None
    update_data = subscription_update.model_dump(exclude_unset=True)

    if (
        "targetPrice" in update_data
        and update_data["targetPrice"] != db_subscription.targetPrice
    ):
        db_subscription.isActive = True  # type: ignore
    if "isActive" in update_data:
        db_subscription.isActive = update_data["isActive"]

    for key, value in update_data.items():
        if key not in ["isActive"]:
            setattr(db_subscription, key, value)

    db.commit()
    db.refresh(db_subscription)
    return db_subscription


def delete_subscription(
    db: Session, subscription_id: int
) -> Optional[models.Subscription]:
    db_subscription = get_subscription(db, subscription_id)
    if not db_subscription:
        return None
    db.delete(db_subscription)
    db.commit()
    return db_subscription
