import os
import platform
import logging
from datetime import datetime
from email.message import EmailMessage
import smtplib
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from app.crud import subscription as crud_subscription, flight
from app.db import schemas
from app.services import booking_url_service

load_dotenv()

EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")

if not EMAIL_USER or not EMAIL_PASS:
    raise ValueError("EMAIL_USER and EMAIL_PASS must be set in environment variables")

logger = logging.getLogger("flight_alerts")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s %(levelname)s: %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)


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
        logger.warning(f"Failed to parse departure date: {e}")
        departure_date = raw_date

    booking_url = flight_details.get("bookingUrl")

    subject = "✈️ Flight Price Alert"

    html_body = f"""
    <html>
    <head></head>
    <body>
        <p>Good news! 🎉</p>
        <p>The flight you were watching has dropped below your target price.</p>
        <p>
            <strong>🛫 Flight:</strong> {flight_details.get('originAirportCode')} ➡️ {flight_details.get('arrivalAirportCode')}<br>
            <strong>📅 Departure Date:</strong> {departure_date}<br>
            <strong>🎯 Your Target Price:</strong> {target_price}€<br>
            <strong>💰 Current Price:</strong> {current_price}€
        </p>
        {"<p><a href='" + booking_url + "' style='display: inline-block; padding: 10px 20px; background-color: #007bff; color: white; text-decoration: none; border-radius: 5px;'>Book Now! ✈️</a></p>" if booking_url else ""}
        <p><i>Note: You will no longer receive alerts for this flight unless you reactivate it.</i></p>
        <p>Happy travels! 🧳</p>
    </body>
    </html>
    """

    plain_text_body = (
        f"Good news! 🎉\n\n"
        f"The flight you were watching has dropped below your target price.\n\n"
        f"🛫 Flight: {flight_details.get('originAirportCode')} ➡ {flight_details.get('arrivalAirportCode')}\n"
        f"📅 Departure Date: {departure_date}\n"
        f"🎯 Your Target Price: {target_price}€\n"
        f"💰 Current Price: {current_price}€\n"
        f"{'Book Now: ' + booking_url + '\n' if booking_url else ''}"
        f"📩 Note: You will no longer receive alerts for this flight unless you reactivate it.\n\n"
        f"Happy travels! 🧳\n"
    )

    msg = EmailMessage()
    msg["From"] = EMAIL_USER
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(plain_text_body)
    msg.add_alternative(html_body, subtype="html")

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(EMAIL_USER, EMAIL_PASS)  # type: ignore
            smtp.send_message(msg)
        logger.info(f"Email sent to {to_email}")
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")


def check_and_send_alerts_for_flights(db: Session, updated_flights_info: list):
    if not updated_flights_info:
        return
    logger.info("Checking subscriptions for recently updated flights...")
    for item in updated_flights_info:
        db_flight = item["flight"]
        old_price = item.get("old_price")

        if old_price is None:
            continue

        subscriptions = crud_subscription.get_active_subscriptions_for_flight_with_notifications_enabled(
            db, db_flight.id
        )

        booking_url = booking_url_service.generate_nouvelair_booking_url(db_flight)

        for sub in subscriptions:
            target_price = sub.targetPrice  # type: ignore
            updated_price = db_flight.price  # type: ignore

            if (old_price > target_price) and (updated_price <= target_price):
                logger.info(f"ALERT TRIGGERED for {sub.email} on Flight {db_flight.id}")
                send_price_alert_email(
                    to_email=sub.email,  # type: ignore
                    flight_details={
                        "originAirportCode": db_flight.departureAirportCode,
                        "arrivalAirportCode": db_flight.arrivalAirportCode,
                        "departureDate": db_flight.departureDate.isoformat(),
                        "bookingUrl": booking_url,
                    },
                    target_price=target_price,  # type: ignore
                    current_price=updated_price,
                )

                sub_update_schema = schemas.SubscriptionUpdate(isActive=False)
                crud_subscription.update_subscription(db, sub.id, sub_update_schema)  # type: ignore
                logger.info(f"Subscription {sub.id} set to inactive after alert.")
            else:
                logger.debug(
                    f"Subscription {sub.id} for {sub.email} (Target: {target_price}€, Prev: {old_price}€, New: {updated_price}€) - No alert needed."
                )
    logger.info("Finished checking subscriptions for updated flights.")
