# In app/services/fetch_flights.py (or a new service file)
# This function contains all the logic that USED to be in the scraper script

import logging
from datetime import datetime
from sqlalchemy.orm import Session
from app.db import models, schemas
from app.crud import flight, flight_price_history

logger = logging.getLogger(__name__)

def process_scraped_flights(db: Session, payload: schemas.ScrapedDataPayload):
    """
    Processes a batch of scraped flights, updates the database, and returns
    a list of flights whose prices have changed for alert notifications.
    """
    updated_flights_for_alerting = []
    new_flights_count = 0
    updated_prices_count = 0

    for scraped_flight in payload.flights:
        # Check if this exact flight (route, date, airline) already exists
        existing_flight = db.query(models.Flight).filter(
            models.Flight.departureDate == scraped_flight.departureDate,
            models.Flight.departureAirportCode == scraped_flight.departureAirportCode,
            models.Flight.arrivalAirportCode == scraped_flight.arrivalAirportCode,
            models.Flight.airlineCode == scraped_flight.airlineCode
        ).first()

        now = datetime.now()

        if not existing_flight:
            # Flight doesn't exist, so create it
            new_flight_db = flight.create_flight(db, flight=schemas.FlightCreate(**scraped_flight.model_dump()))
            new_flights_count += 1
            
            # Create its first price history record
            history_data = schemas.FlightPriceHistoryCreate(
                flightId=new_flight_db.id,
                price=scraped_flight.price,
                priceEur=scraped_flight.priceEur,
                timestamp=now
            )
            flight_price_history.create_price_history(db, history_data)
        
        else:
            # Flight exists, check if the original price has changed
            # Use a small tolerance for comparing floats
            if abs(existing_flight.price - scraped_flight.price) > 0.01:
                old_price_eur = existing_flight.priceEur  # Capture old EUR price for alerts
                
                # Update the flight with the new price information
                update_data = schemas.FlightUpdate(
                    price=scraped_flight.price,
                    priceEur=scraped_flight.priceEur
                )
                flight.update_flight(db, flight_id=existing_flight.id, flight_update=update_data)
                updated_prices_count += 1

                # Create a new price history record for the change
                history_data = schemas.FlightPriceHistoryCreate(
                    flightId=existing_flight.id,
                    price=scraped_flight.price,
                    priceEur=scraped_flight.priceEur,
                    timestamp=now
                )
                flight_price_history.create_price_history(db, history_data)
                
                # Add the necessary info for the alert service
                updated_flights_for_alerting.append({
                    "flight": existing_flight,
                    "old_price_eur": old_price_eur
                })

    logger.info(f"Processed report: {new_flights_count} new flights, {updated_prices_count} updated prices.")
    return updated_flights_for_alerting