"""Settings tests: DATABASE_URL normalization for Railway/Heroku-style URLs."""

from core.config import Settings


def test_postgres_scheme_normalized():
    s = Settings(DATABASE_URL="postgres://user:pass@host:5432/db")
    assert s.DATABASE_URL == "postgresql+psycopg://user:pass@host:5432/db"


def test_postgresql_scheme_normalized():
    s = Settings(DATABASE_URL="postgresql://user:pass@host:5432/db")
    assert s.DATABASE_URL == "postgresql+psycopg://user:pass@host:5432/db"


def test_explicit_driver_unchanged():
    s = Settings(DATABASE_URL="postgresql+psycopg://user:pass@host:5432/db")
    assert s.DATABASE_URL == "postgresql+psycopg://user:pass@host:5432/db"


def test_sqlite_unchanged():
    s = Settings(DATABASE_URL="sqlite:////tmp/test.db")
    assert s.DATABASE_URL == "sqlite:////tmp/test.db"
