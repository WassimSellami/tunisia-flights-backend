from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv
from sqlalchemy.exc import OperationalError

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)  # type: ignore
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

try:
    with engine.connect() as connection:
        print("✅ Successfully connected to the database.")
except OperationalError as e:
    print("❌ Failed to connect to the database.")
    print(f"Error: {e}")
