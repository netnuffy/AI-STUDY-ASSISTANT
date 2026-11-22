"""SQLAlchemy engine + session factory. Importing this module does NOT connect
to the database (the engine connects lazily), so the app can import safely."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.config import get_settings

settings = get_settings()

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db():
    """FastAPI dependency: yields a DB session, closes it afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
