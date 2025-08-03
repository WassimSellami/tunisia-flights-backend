from datetime import datetime
from app.crud import flight, flight_price_history, airport
from app.db import schemas, models
from sqlalchemy.orm import Session
import requests
import time
from seleniumwire import webdriver
from selenium.webdriver.chrome.options import Options
import warnings
from itertools import product  # Import product for combinations

warnings.filterwarnings("ignore", category=UserWarning, module="seleniumwire")


NOUVELAIR_AVAILABILITY_API = "https://webapi.nouvelair.com/api/reservation/availability"
NOUVELAIR_URL = "https://www.nouvelair.com/"
CURRENCY = 2  # EUR
AIRLINE_CODE = "BJ"
API_KEY = None


def capture_api_key():
    global API_KEY
    options = {"disable_encoding": True}

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(seleniumwire_options=options, options=chrome_options)

    try:
        driver.get(NOUVELAIR_URL)
        time.sleep(10)

        for request in driver.requests:
            if (
                request.response
                and "webapi.nouvelair.com/api" in request.url
                and request.headers.get("x-api-key")
            ):
                API_KEY = request.headers["x-api-key"]
                print("API Key captured:", API_KEY)
                break

        if not API_KEY:
            print("API Key not found in captured requests.")
    finally:
        driver.quit()


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
        print("Error:", e)
        return []


def fetch_and_store_flights(db: Session):
    global API_KEY
    print("Capturing API key...")
    capture_api_key()
    if API_KEY is None:
        print("Cannot proceed without API key.")
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
        print("No dynamic routes generated. Ensure TN and DE airports exist in DB.")
        return []

    processed_flights_info = []
    new_flights_count = 0
    updated_prices_count = 0

    for departure_airport, arrival_airport in dynamic_routes:
        print(f"Fetching flights from {departure_airport} to {arrival_airport}...")

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
                print(f"Skipping invalid date {date_str}: {e}")
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

                print(
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

                    print(
                        f"Updated price for flight on {departure_date} {departure_airport}->{arrival_airport} from {old_price} to {price} Eur"
                    )
                    processed_flights_info.append(
                        {"flight": existing_flight, "old_price": old_price}
                    )
                    updated_prices_count += 1

    print(
        f"\nSummary: {new_flights_count} new flights added, {updated_prices_count} prices updated.\n"
    )
    return processed_flights_info


# Example of how you would run this (e.g., from a management script or a Fastapi background task)
# if __name__ == "__main__":
#     from app.db.session import SessionLocal # Import SessionLocal here
#     db = SessionLocal()
#     try:
#         print("Starting flight data fetch...")
#         fetched_data = fetch_and_store_flights(db)
#         print("Flight data fetch completed.")
#         # You can then use fetched_data to trigger alerts if this script is also part of your alert mechanism
#     finally:
#         db.close()
