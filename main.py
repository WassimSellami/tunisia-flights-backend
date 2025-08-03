import os
import logging
from sqlalchemy import text
from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.endpoints import (
    airline,
    flight,
    flight_price_history,
    subscription,
    airport,
    user,
)
from apscheduler.schedulers.background import BackgroundScheduler
from app.services.fetch_flights import fetch_and_store_flights
from app.services.email_alerts import check_and_send_alerts_for_flights
from app.db.session import SessionLocal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# Keep this if you still have seleniumwire in requirements.txt (though you shouldn't after Playwright)
# If removed, this line can be removed as well.
logging.getLogger("seleniumwire").setLevel(logging.WARNING)

scheduler = BackgroundScheduler()


def scheduled_job():
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        logger.info("🚀 Running scheduled flight fetch job...")
        updateFlights = fetch_and_store_flights(db)
        logger.info("✅ Flight fetch complete.")
        check_and_send_alerts_for_flights(db, updateFlights)
    except Exception as e:
        logger.error(f"❌ Scheduled job failed: {e}")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application lifespan startup initiated.")
    try:
        scheduler.add_job(scheduled_job, "cron", minute=16)
        scheduler.start()
        logger.info("✅ Scheduler started.")
        yield
        logger.info("Application lifespan shutdown initiated.")
        scheduler.shutdown()
        logger.info("🛑 Scheduler shut down.")
    except Exception as e:
        logger.critical(
            f"Unhandled exception during lifespan startup: {e}", exc_info=True
        )
        # Re-raise the exception to prevent the app from starting in a bad state
        raise


app = FastAPI(lifespan=lifespan)

origins = os.getenv("CORS_ORIGINS", "").split(",")
logger.info(f"Configuring CORS with origins: {origins}")  # Log origins

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_methods=["*"],
    allow_origins=origins,  # Use the `origins` variable here. Don't hardcode "*" unless it's intended.
    allow_headers=["*"],
)

logger.info("Attempting to define /ping endpoint...")


@app.get("/ping")
async def ping():
    logger.info("'/ping' endpoint hit. Returning pong.")  # Added logging
    return {"pong"}


logger.info("'/ping' endpoint defined.")


logger.info("Attempting to include API routers...")
try:
    app.include_router(user.router)
    logger.info("Included user router.")
    app.include_router(airline.router)
    logger.info("Included airline router.")
    app.include_router(flight.router)
    logger.info("Included flight router.")
    app.include_router(flight_price_history.router)
    logger.info("Included flight_price_history router.")
    app.include_router(subscription.router)
    logger.info("Included subscription router.")
    app.include_router(airport.router)
    logger.info("Included airport router.")
    logger.info("All API routers included successfully.")
except Exception as e:
    logger.critical(f"Failed to include API routers: {e}", exc_info=True)
    # If router inclusion fails, the app won't serve anything.
    # It might be beneficial to raise an exception here to fail the deployment.
    # raise RuntimeError("Router inclusion failed") from e
