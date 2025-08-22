import asyncio

from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.services import scraper_service

router = APIRouter(prefix="/scraper", tags=["scraper"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def run_scrapers(db: Session):
    await asyncio.gather(
        scraper_service.run_nouvelair_job(db), scraper_service.run_tunisair_job(db)
    )


@router.get("/", status_code=202)
async def scrape(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    background_tasks.add_task(run_scrapers, db)
    return {"message": "Scraper jobs started in the background."}
