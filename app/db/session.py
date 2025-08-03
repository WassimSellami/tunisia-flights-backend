import os
import logging
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")

logger = logging.getLogger("database")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s %(levelname)s: %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

try:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)  # type: ignore
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    with engine.connect() as connection:
        logger.info("✅ Successfully connected to the database.")
except OperationalError as e:
    logger.error("❌ Failed to connect to the database.")
    logger.error(f"Error: {e}")
    raise
