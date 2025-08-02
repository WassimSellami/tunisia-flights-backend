from app.db import models


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
