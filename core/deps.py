from typing import Generator
from sqlalchemy.orm import Session
from db.session import SessionLocal
from core.config import get_settings, Settings

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
