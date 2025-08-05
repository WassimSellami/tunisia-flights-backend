import os
import logging
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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles application startup and shutdown events.
    The scheduler has been removed as scraping is now handled by an external service.
    """
    logger.info("✅ Main backend service starting up...")
    yield
    logger.info("🛑 Main backend service shutting down.")


app = FastAPI(lifespan=lifespan)

origins = os.getenv("CORS_ORIGINS", "").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], #change later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/ping")
async def ping():
    return {"status": "alive"}


app.include_router(user.router)
app.include_router(airline.router)
app.include_router(flight.router)
app.include_router(flight_price_history.router)
app.include_router(subscription.router)
app.include_router(airport.router)