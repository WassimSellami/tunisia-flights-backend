import logging
import os
import time
from datetime import datetime, date
from itertools import product
from typing import List, Dict, Any, Tuple

import httpx
from bs4 import BeautifulSoup
from dateutil.relativedelta import relativedelta
from playwright.async_api import async_playwright
from sqlalchemy.orm import Session

from app.crud import flight, flight_price_history, airport
from app.db import models, schemas

logger = logging.getLogger(__name__)

NOUVELAIR_AVAILABILITY_API = "https://webapi.nouvelair.com/api/reservation/availability"
NOUVELAIR_URL = "https://www.nouvelair.com/"
NOUVELAIR_CURRENCY_ID = 2
NOUVELAIR_AIRLINE_CODE = "BJ"
nouvelair_api_key: str | None = None

TUNISAIR_BASE_URL_DE = "https://flights.tunisair.com/en-de/prices/per-day"
TUNISAIR_BASE_URL_BE = "https://flights.tunisair.com/en-be/prices/per-day"
TUNISAIR_BASE_URL_TN = "https://flights.tunisair.com/en-tn/prices/per-day"
TUNISAIR_EXCHANGE_RATE_API_URL = (
    "https://v6.exchangerate-api.com/v6/{api_key}/latest/TND"
)
TUNISAIR_AIRLINE_CODE = "TU"
TUNISAIR_MONTHS_TO_SEARCH = 4
TUNISAIR_DEFAULT_TRIP_TYPE = "O"
TUNISAIR_DEFAULT_TRIP_DURATION = "0"
TUNISAIR_REQUEST_RETRIES = 3

TUNISAIR_VALID_ROUTES_DE_TO_TN: List[Tuple[str, str]] = [
    ("MUC", "TUN"),
    ("MUC", "MIR"),
    ("MUC", "DJE"),
    ("FRA", "TUN"),
    ("FRA", "DJE"),
    ("DUS", "TUN"),
    ("BRU", "TUN"),
]
TUNISAIR_VALID_ROUTES_TN_TO_DE: List[Tuple[str, str]] = [
    ("TUN", "BRU"),
    ("TUN", "MUC"),
    ("TUN", "FRA"),
    ("TUN", "DUS"),
    ("MIR", "MUC"),
    ("DJE", "MUC"),
    ("DJE", "FRA"),
]


def process_scraped_flights(db: Session, payload: schemas.ScrapedDataPayload):
    updated_flights_for_alerting = []
    new_flights_count = 0
    updated_prices_count = 0

    for scraped_flight in payload.flights:
        existing_flight = (
            db.query(models.Flight)
            .filter(
                models.Flight.departureDate == scraped_flight.departureDate,
                models.Flight.departureAirportCode
                == scraped_flight.departureAirportCode,
                models.Flight.arrivalAirportCode == scraped_flight.arrivalAirportCode,
                models.Flight.airlineCode == scraped_flight.airlineCode,
            )
            .first()
        )
        now = datetime.now()
        if not existing_flight:
            new_flight_db = flight.create_flight(
                db, flight=schemas.FlightCreate(**scraped_flight.model_dump())
            )
            new_flights_count += 1
            history_data = schemas.FlightPriceHistoryCreate(
                flightId=new_flight_db.id,
                price=scraped_flight.price,
                priceEur=scraped_flight.priceEur,
                timestamp=now,
            )
            flight_price_history.create_price_history(db, history_data)
        else:
            if abs(float(existing_flight.price) - float(scraped_flight.price)) > 0.01:
                old_price_eur = existing_flight.priceEur
                update_data = schemas.FlightUpdate(
                    price=scraped_flight.price, priceEur=scraped_flight.priceEur
                )
                flight.update_flight(
                    db, flight_id=existing_flight.id, flight_update=update_data
                )
                updated_prices_count += 1
                history_data = schemas.FlightPriceHistoryCreate(
                    flightId=existing_flight.id,
                    price=scraped_flight.price,
                    priceEur=scraped_flight.priceEur,
                    timestamp=now,
                )
                flight_price_history.create_price_history(db, history_data)
                updated_flights_for_alerting.append(
                    {"flight": existing_flight, "old_price_eur": old_price_eur}
                )
    logger.info(
        f"Processed report: {new_flights_count} new flights, {updated_prices_count} updated prices."
    )
    return updated_flights_for_alerting


async def _nouvelair_capture_api_key():
    global nouvelair_api_key
    logger.info("Launching headless browser to capture Nouvelair API key...")
    captured_key = None
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        async def handle_request(request):
            nonlocal captured_key
            if (
                captured_key is None
                and "webapi.nouvelair.com/api" in request.url
                and "x-api-key" in request.headers
            ):
                captured_key = request.headers["x-api-key"]
                logger.info(f"Nouvelair API Key captured: {captured_key[:10]}...")

        page.on("request", handle_request)
        try:
            await page.goto(NOUVELAIR_URL, wait_until="domcontentloaded", timeout=45000)
            start_time = time.time()
            while captured_key is None and time.time() - start_time < 30:
                await page.wait_for_timeout(100)
        except Exception as e:
            logger.error(f"Error during Playwright API key capture for Nouvelair: {e}")
        finally:
            await browser.close()
    if captured_key:
        nouvelair_api_key = captured_key
        logger.info("Nouvelair API Key successfully secured.")
    else:
        logger.error("Failed to capture Nouvelair API key within the time limit.")


async def _get_nouvelair_flight_availability(
    session: httpx.AsyncClient, dep_code: str, dest_code: str
) -> List[Dict[str, Any]]:
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Origin": NOUVELAIR_URL,
        "x-api-key": nouvelair_api_key or "",
    }
    params = {
        "departure_code": dep_code,
        "destination_code": dest_code,
        "trip_type": 1,
        "currency_id": NOUVELAIR_CURRENCY_ID,
    }
    try:
        res = await session.get(
            NOUVELAIR_AVAILABILITY_API, params=params, headers=headers, timeout=20
        )
        res.raise_for_status()
        return res.json().get("data", [])
    except httpx.RequestError as e:
        logger.error(
            f"Error fetching Nouvelair availability for {dep_code}->{dest_code}: {e}"
        )
        return []


async def run_nouvelair_job(db: Session):
    logger.info("--- Starting Nouvelair scraper run ---")
    await _nouvelair_capture_api_key()
    if not nouvelair_api_key:
        logger.critical("Nouvelair scraper run aborted: Could not obtain API key.")
        return
    airports_list = airport.get_airports(db)
    if not airports_list:
        logger.critical(
            "Nouvelair scraper run aborted: Could not fetch airport list from backend."
        )
        return
    tunisian_airports = [a.code for a in airports_list if a.country == "TN"]
    german_airports = [a.code for a in airports_list if a.country == "DE"]
    routes = list(product(tunisian_airports, german_airports)) + list(
        product(german_airports, tunisian_airports)
    )
    logger.info("--- Starting Nouvelair scraping for routes ---")
    scraped_data_payload = schemas.ScrapedDataPayload(flights=[])

    async with httpx.AsyncClient() as session:
        for dep_code, arr_code in routes:
            for f in await _get_nouvelair_flight_availability(
                session, dep_code, arr_code
            ):
                try:
                    price = float(f["price"])
                    if price <= 0:
                        continue
                    departure_date = datetime.strptime(f["date"], "%Y-%m-%d")
                    scraped_data_payload.flights.append(
                        schemas.ScrapedFlight(
                            departureDate=departure_date,
                            price=price,
                            priceEur=price,
                            departureAirportCode=dep_code,
                            arrivalAirportCode=arr_code,
                            airlineCode=NOUVELAIR_AIRLINE_CODE,
                        )
                    )
                except (ValueError, TypeError, KeyError) as e:
                    logger.warning(
                        f"Skipping malformed Nouvelair flight record: {f}. Error: {e}"
                    )
            time.sleep(
                1
            )  # Consider removing or making this async if performance is critical

    try:
        process_scraped_flights(db, scraped_data_payload)
    except Exception as e:
        logger.critical(
            f"A fatal error occurred while reporting Nouvelair data. Run aborted. Error: {e}"
        )
        raise
    logger.info("--- Nouvelair scraper run finished successfully ---")


async def _get_tunisair_exchange_rate(session: httpx.AsyncClient) -> float:
    api_key = os.getenv("EXCHANGE_RATE_API_KEY")
    fallback_eur_rate = 0.29
    if not api_key:
        logger.warning(
            f"EXCHANGE_RATE_API_KEY not found. Using fallback rate: 1 TND = {fallback_eur_rate:.4f} EUR"
        )
        return fallback_eur_rate
    url = TUNISAIR_EXCHANGE_RATE_API_URL.format(api_key=api_key)
    for attempt in range(TUNISAIR_REQUEST_RETRIES):
        try:
            response = await session.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            if data.get("result") == "success":
                rate = data["conversion_rates"]["EUR"]
                logger.info(
                    f"Successfully fetched exchange rate: 1 TND = {rate:.4f} EUR"
                )
                return rate
        except httpx.RequestError as e:
            logger.warning(
                f"Attempt {attempt + 1}/{TUNISAIR_REQUEST_RETRIES} to fetch exchange rate failed: {e}"
            )
            if attempt < TUNISAIR_REQUEST_RETRIES - 1:
                time.sleep(1)
    logger.error(
        f"Failed to fetch exchange rate after {TUNISAIR_REQUEST_RETRIES} attempts. Using fallback."
    )
    return fallback_eur_rate


def _extract_tunisair_prices(
    html: str, is_eur_native: bool, conversion_rate: float
) -> List[Dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    found_flights = []
    for td in soup.find_all("td", class_="available"):
        date_str = td.get("data-departure")
        price_div = td.find("div", class_="val_price_offre")
        if not (
            date_str
            and price_div
            and (price_text := price_div.get_text(strip=True))
            and price_text != "-"
        ):
            continue
        try:
            departure_date = datetime.strptime(date_str, "%Y-%m-%d")
            flight_data = {}
            if is_eur_native and "EUR" in price_text:
                price_str = (
                    price_text.replace(" ", "").replace(",", ".").replace("EUR", "")
                )
                price_val = round(float(price_str), 2)
                flight_data = {"price": price_val, "priceEur": price_val}
            elif not is_eur_native and "TND" in price_text:
                price_str = (
                    price_text.replace(" ", "").replace(",", ".").replace("TND", "")
                )
                price_tnd = round(float(price_str), 3)
                flight_data = {
                    "price": price_tnd,
                    "priceEur": round(price_tnd * conversion_rate, 2),
                }
            else:
                continue
            flight_data["departureDate"] = departure_date
            found_flights.append(flight_data)
        except (ValueError, TypeError) as e:
            logger.warning(
                f"Could not parse Tunisair record '{date_str}' | '{price_text}'. Error: {e}"
            )
    return found_flights


async def _scrape_tunisair_route(
    session: httpx.AsyncClient,
    dep_code: str,
    arr_code: str,
    is_eur_native: bool,
    conversion_rate: float = 1.0,
) -> List[Dict[str, Any]]:
    base_url = TUNISAIR_BASE_URL_TN
    if is_eur_native:
        base_url = TUNISAIR_BASE_URL_BE if dep_code == "BRU" else TUNISAIR_BASE_URL_DE

    route_flights = []
    today = date.today()
    search_dates = [today.strftime("%Y-%m-%d")] + [
        (today + relativedelta(months=i)).strftime("%Y-%m-01")
        for i in range(1, TUNISAIR_MONTHS_TO_SEARCH)
    ]
    for search_date in search_dates:
        params = {
            "date": search_date,
            "from": dep_code,
            "to": arr_code,
            "tripDuration": TUNISAIR_DEFAULT_TRIP_DURATION,
            "tripType": TUNISAIR_DEFAULT_TRIP_TYPE,
        }
        html_view = None
        for attempt in range(TUNISAIR_REQUEST_RETRIES):
            try:
                response = await session.get(base_url, params=params, timeout=20)
                response.raise_for_status()
                html_view = response.json().get("view", "")
                break
            except httpx.RequestError as e:
                logger.warning(
                    f"Attempt {attempt + 1}/{TUNISAIR_REQUEST_RETRIES} failed for Tunisair {dep_code}->{arr_code} on {search_date}: {e}"
                )
                if attempt < TUNISAIR_REQUEST_RETRIES - 1:
                    time.sleep(1)

        if html_view:
            extracted_flights = _extract_tunisair_prices(
                html_view, is_eur_native, conversion_rate
            )
            for flight_data in extracted_flights:
                flight_data["departureAirportCode"] = dep_code
                flight_data["arrivalAirportCode"] = arr_code
            route_flights.extend(extracted_flights)
        else:
            logger.error(
                f"Failed to fetch Tunisair data for {dep_code}->{arr_code} on {search_date} after retries."
            )
        time.sleep(0.5)
    return route_flights


async def run_tunisair_job(db: Session):
    logger.info("--- Starting Tunisair scraper run ---")

    all_scraped_flights = []

    async with httpx.AsyncClient() as session:
        logger.info(
            "--- Scraping Tunisair flights from Germany to Tunisia (EUR native) ---"
        )
        for dep, arr in TUNISAIR_VALID_ROUTES_DE_TO_TN:
            all_scraped_flights.extend(
                await _scrape_tunisair_route(session, dep, arr, is_eur_native=True)
            )

        logger.info(
            "--- Scraping Tunisair flights from Tunisia to Germany (TND native) ---"
        )
        conversion_rate = await _get_tunisair_exchange_rate(session)
        for dep, arr in TUNISAIR_VALID_ROUTES_TN_TO_DE:
            all_scraped_flights.extend(
                await _scrape_tunisair_route(
                    session,
                    dep,
                    arr,
                    is_eur_native=False,
                    conversion_rate=conversion_rate,
                )
            )

    scraped_data_payload = schemas.ScrapedDataPayload(flights=[])
    for flight_dict in all_scraped_flights:
        scraped_data_payload.flights.append(
            schemas.ScrapedFlight(
                departureDate=flight_dict["departureDate"],
                price=flight_dict["price"],
                priceEur=flight_dict["priceEur"],
                departureAirportCode=flight_dict["departureAirportCode"],
                arrivalAirportCode=flight_dict["arrivalAirportCode"],
                airlineCode=TUNISAIR_AIRLINE_CODE,
            )
        )

    try:
        process_scraped_flights(db, scraped_data_payload)
    except Exception as e:
        logger.critical(
            f"A fatal error occurred while reporting Tunisair data. Run aborted. Error: {e}"
        )
        raise
    logger.info("--- Tunisair scraper run finished successfully ---")
