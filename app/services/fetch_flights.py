import time
import logging
import requests
from itertools import product
from datetime import datetime
from playwright.sync_api import sync_playwright
from sqlalchemy.orm import Session
from app.crud import flight, flight_price_history, airport
from app.db import schemas, models

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

NOUVELAIR_AVAILABILITY_API = "https://webapi.nouvelair.com/api/reservation/availability"
NOUVELAIR_URL = "https://www.nouvelair.com/"
CURRENCY = 2
AIRLINE_CODE = "BJ"
API_KEY = None


def capture_api_key():
    global API_KEY
    if API_KEY:
        logger.info(
            "API Key already captured (from previous job run), skipping re-capture."
        )
        return

    captured_key = None
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        key_found_and_ready_to_exit = False

        def handle_request(request):
            nonlocal captured_key
            nonlocal key_found_and_ready_to_exit
            if (
                captured_key is None
                and "webapi.nouvelair.com/api" in request.url
                and "x-api-key" in request.headers
            ):
                captured_key = request.headers["x-api-key"]
                logger.info(f"API Key captured: {captured_key[:5]}...")
                key_found_and_ready_to_exit = True

        page.on("request", handle_request)

        try:
            page.goto(NOUVELAIR_URL, wait_until="domcontentloaded", timeout=45000)

            start_time = time.time()
            while not key_found_and_ready_to_exit and (time.time() - start_time < 30):
                page.wait_for_timeout(1000)

            if captured_key:
                API_KEY = captured_key
                logger.info("Playwright session completed, API Key secured.")
            else:
                logger.error(
                    "API Key not found in captured requests within allowed time."
                )

        except Exception as e:
            logger.error(f"Error during Playwright API key capture: {e}")
        finally:
            browser.close()


def get_nouvelair_flight_availability(
    departure_code, destination_code, currency_id, trip_type=1
):
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": NOUVELAIR_URL,
        "Origin": NOUVELAIR_URL,
        "Accept": "application/json",
        "X-API-Key": API_KEY,
    }
    params = {
        "departure_code": departure_code.upper(),
        "destination_code": destination_code.upper(),
        "trip_type": trip_type,
        "currency_id": currency_id,
    }

    try:
        res = requests.get(NOUVELAIR_AVAILABILITY_API, params=params, headers=headers)
        res.raise_for_status()
        return res.json().get("data", [])
    except Exception as e:
        logger.error(f"Error fetching availability: {e}")
        return []


def fetch_and_store_flights(db: Session):
    global API_KEY
    logger.info("Capturing API key...")
    capture_api_key()
    if API_KEY is None:
        logger.error("Cannot proceed without API key.")
        return []

    all_airports = airport.get_airports(db)
    tunisian_airports = [
        a.code for a in all_airports if getattr(a, "country", None) == "TN"
    ]
    german_airports = [
        a.code for a in all_airports if getattr(a, "country", None) == "DE"
    ]

    dynamic_routes = []
    for tn_airport_code, de_airport_code in product(tunisian_airports, german_airports):
        dynamic_routes.append((tn_airport_code, de_airport_code))
    for de_airport_code, tn_airport_code in product(german_airports, tunisian_airports):
        dynamic_routes.append((de_airport_code, tn_airport_code))

    if not dynamic_routes:
        logger.warning(
            "No dynamic routes generated. Ensure TN and DE airports exist in DB."
        )
        return []

    processed_flights_info = []
    new_flights_count = 0
    updated_prices_count = 0

    for departure_airport, arrival_airport in dynamic_routes:
        logger.info(
            f"Fetching flights from {departure_airport} to {arrival_airport}..."
        )

        flights = get_nouvelair_flight_availability(
            departure_airport, arrival_airport, CURRENCY
        )

        for f in flights:
            date_str = f.get("date")
            price = int(f.get("price"))

            if price <= 0:
                continue

            try:
                departure_date = datetime.strptime(date_str, "%Y-%m-%d")
            except Exception as e:
                logger.warning(f"Skipping invalid date {date_str}: {e}")
                continue

            existing_flight = (
                db.query(models.Flight)
                .filter_by(
                    departureDate=departure_date,
                    departureAirportCode=departure_airport,
                    arrivalAirportCode=arrival_airport,
                    airlineCode=AIRLINE_CODE,
                )
                .first()
            )

            now = datetime.now()

            if not existing_flight:
                flight_data = schemas.FlightCreate(
                    departureDate=departure_date,
                    price=price,
                    departureAirportCode=departure_airport,
                    arrivalAirportCode=arrival_airport,
                    airlineCode=AIRLINE_CODE,
                )
                db_flight = flight.create_flight(db, flight_data)

                price_history_data = schemas.FlightPriceHistoryCreate(
                    flightId=db_flight.id,  # type: ignore
                    price=price,
                    timestamp=now,
                )
                flight_price_history.create_price_history(db, price_history_data)

                logger.info(
                    f"Added new flight on {departure_date} {departure_airport}->{arrival_airport} price: {price} Eur"
                )
                new_flights_count += 1

            else:
                old_price = existing_flight.price
                if old_price != price:  # type: ignore
                    existing_flight.price = price  # type: ignore
                    db.commit()
                    db.refresh(existing_flight)

                    price_history_data = schemas.FlightPriceHistoryCreate(
                        flightId=existing_flight.id,  # type: ignore
                        price=price,
                        timestamp=now,
                    )
                    flight_price_history.create_price_history(db, price_history_data)

                    logger.info(
                        f"Updated price for flight on {departure_date} {departure_airport}->{arrival_airport} from {old_price} to {price} Eur"
                    )
                    processed_flights_info.append(
                        {"flight": existing_flight, "old_price": old_price}
                    )
                    updated_prices_count += 1

    logger.info(
        f"{new_flights_count} new flights added, {updated_prices_count} prices updated."
    )
    return processed_flights_info
