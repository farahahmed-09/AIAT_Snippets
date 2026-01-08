
from typing import Generator
from src.app.core.database import SessionLocal


def get_db() -> Generator:
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()
