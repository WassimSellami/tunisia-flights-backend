from app.db import models
from datetime import datetime

def generate_nouvelair_booking_url(flight: models.Flight) -> str | None:
    if getattr(flight, "airlineCode", None) != "BJ":
        return None

    departure_date_formatted = flight.departureDate.strftime("%d.%m.%Y")

    base_url = "https://booking.nouvelair.com/ibe/availability"
    params = {
        "tripType": "ONE_WAY",
        "passengerQuantities%5B0%5D.passengerType": "ADULT",
        "passengerQuantities%5B0%5D.quantity": 1,
        "currency": "EUR",
        "depPort": flight.departureAirportCode,
        "arrPort": flight.arrivalAirportCode,
        "departureDate": departure_date_formatted,
        "lang": "en",
    }

    query_string = "&".join([f"{key}={value}" for key, value in params.items()])

    return f"{base_url}?{query_string}"


def generate_tunisair_booking_url(flight: models.Flight) -> str | None:
    if getattr(flight, "airlineCode", None) != "TU":
        return None

    departure_date_formatted = flight.departureDate.strftime("%d-%m-%Y")

    base_url = "https://www.tunisair.com/en/vol_reservation/send-reservation"
    params = {
        "from_destination": flight.departureAirportCode,
        "to_destination": flight.arrivalAirportCode,
        "vol_type": "O",
        "start_date": departure_date_formatted,
        "end_date": departure_date_formatted,
        "adults": 1,
        "teenagers": 0,
        "kids": 0,
        "babies": 0,
        "promotion_code": "",
        "source": "DESKTOP",
        "currency": "",
        "ibe_configuration": "booking",
    }

    query_string = "&".join([f"{key}={value}" for key, value in params.items()])

    return f"{base_url}?{query_string}"


def generate_booking_url(flight: models.Flight) -> str | None:
    airline_code = getattr(flight, "airlineCode", None)

    if airline_code == "BJ":
        return generate_nouvelair_booking_url(flight)
    elif airline_code == "TU":
        return generate_tunisair_booking_url(flight)
    else:
        return None