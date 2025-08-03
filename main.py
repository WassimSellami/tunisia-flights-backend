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
    scheduler.add_job(scheduled_job, "cron", minute=32)
    scheduler.start()
    logger.info("✅ Scheduler started.")
    yield
    scheduler.shutdown()
    logger.info("🛑 Scheduler shut down.")


app = FastAPI(lifespan=lifespan)

origins = os.getenv("CORS_ORIGINS", "").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/ping")
async def ping():
    return {"pong"}


app.include_router(user.router)
app.include_router(airline.router)
app.include_router(flight.router)
app.include_router(flight_price_history.router)
app.include_router(subscription.router)
app.include_router(airport.router)
