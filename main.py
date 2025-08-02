from sqlalchemy import text
from fastapi import FastAPI  # type: ignore
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware  # type: ignore

from app.api.v1.endpoints import (
    airline,
    flight,
    flight_price_history,
    subscription,
    airport,
    user,
)

from apscheduler.schedulers.background import BackgroundScheduler  # type: ignore
from app.services.fetch_flights import (
    fetch_and_store_flights,
)
from app.services.email_alerts import (
    check_and_send_alerts_for_flights,
)
from app.db.session import SessionLocal


scheduler = BackgroundScheduler()


def scheduled_job():
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        print("🚀 Running scheduled flight fetch job...")
        updateFlights = fetch_and_store_flights(db)
        print("✅ Flight fetch complete.")

        check_and_send_alerts_for_flights(db, updateFlights)

    except Exception as e:
        print(f"❌ Scheduled job failed: {e}")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.add_job(scheduled_job, "cron", minute=16)
    scheduler.start()
    print("✅ Scheduler started.")
    yield
    scheduler.shutdown()
    print("🛑 Scheduler shut down.")


app = FastAPI(lifespan=lifespan)

origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(user.router)
app.include_router(airline.router)
app.include_router(flight.router)
app.include_router(flight_price_history.router)
app.include_router(subscription.router)
app.include_router(airport.router)
