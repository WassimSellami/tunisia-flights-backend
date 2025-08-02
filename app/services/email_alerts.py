from sqlalchemy.orm import Session
from app.crud import subscription as crud_subscription, flight
from app.db import schemas
import smtplib
from datetime import datetime
from email.message import EmailMessage
import os
from dotenv import load_dotenv
import platform

from app.db.session import SessionLocal

load_dotenv()
EMAIL_USER = os.getenv("EMAIL_USER", "wrongEmail")
EMAIL_PASS = os.getenv("EMAIL_PASS", "wrongPassword")


def send_price_alert_email(
    to_email: str, flight_details: dict, target_price: float, current_price: float
):
    raw_date = flight_details.get("departureDate")
    day_format = "%#d" if platform.system() == "Windows" else "%-d"

    try:
        if isinstance(raw_date, datetime):
            departure_date = raw_date.strftime(f"{day_format} %b %Y")
        else:
            departure_date = datetime.fromisoformat(str(raw_date)).strftime(
                f"{day_format} %b %Y"
            )
    except Exception as e:
        print(f"⚠️ Failed to parse departure date: {e}")
        departure_date = raw_date

    subject = "✈️ Flight Price Alert"
    body = (
        f"Good news! 🎉\n\n"
        f"The flight you were watching has dropped below your target price.\n\n"
        f"🛫 Flight: {flight_details.get('originAirportCode')} ➡ {flight_details.get('arrivalAirportCode')}\n"
        f"📅 Departure Date: {departure_date}\n"
        f"🎯 Your Target Price: {target_price}€\n"
        f"💰 Current Price: {current_price}€\n"
        f"📩 Note: You will no longer receive alerts for this flight unless you reactivate it.\n\n"
        f"Happy travels! 🧳\n"
    )

    msg = EmailMessage()
    msg["From"] = EMAIL_USER
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(EMAIL_USER, EMAIL_PASS)
            smtp.send_message(msg)
            print(f"✅ Email sent to {to_email}")
    except Exception as e:
        print(f"❌ Failed to send email to {to_email}: {e}")


def check_and_send_alerts_for_flights(db: Session, updated_flights_info: list):
    if not updated_flights_info:
        return
    print("🔎 Checking subscriptions for recently updated flights...")
    for item in updated_flights_info:
        db_flight = item["flight"]
        old_price = item["old_price"]

        if old_price is None:
            continue

        subscriptions_for_this_flight = crud_subscription.get_active_subscriptions_for_flight_with_notifications_enabled(
            db, db_flight.id
        )

        for sub in subscriptions_for_this_flight:
            target_price = sub.targetPrice
            updated_price = db_flight.price
            if (old_price > target_price) and (updated_price <= target_price):
                print(f"🚨 ALERT TRIGGERED for {sub.email} on Flight {db_flight.id}!")
                send_price_alert_email(
                    to_email=sub.email,  # type: ignore
                    flight_details={
                        "originAirportCode": db_flight.departureAirportCode,
                        "arrivalAirportCode": db_flight.arrivalAirportCode,
                        "departureDate": db_flight.departureDate.isoformat(),
                    },
                    target_price=target_price,  # type: ignore
                    current_price=updated_price,
                )

                sub_update_schema = schemas.SubscriptionUpdate(isActive=False)
                crud_subscription.update_subscription(db, sub.id, sub_update_schema)  # type: ignore
                print(f"    Subscription {sub.id} set to inactive after alert.")
            else:
                print(
                    f"  Subscription {sub.id} for {sub.email} (Target: {target_price}€, Prev: {old_price}€, New: {updated_price}€) - No alert needed for drop."
                )
    print("✅ Finished checking subscriptions for updated flights.")


if __name__ == "__main__":
    db = SessionLocal()
    try:
        my_flight = flight.get_flight(db, 28)
        check_and_send_alerts_for_flights(db, [{"flight": my_flight, "old_price": 150}])
    finally:
        db.close()
