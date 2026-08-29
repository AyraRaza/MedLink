from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

# SQLite needs this connect_arg for multi-threaded FastAPI use; Postgres doesn't.
connect_args = (
    {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
)

engine_options = {"connect_args": connect_args, "pool_pre_ping": True}
if not settings.DATABASE_URL.startswith("sqlite"):
    engine_options.update(pool_size=10, max_overflow=10)

engine = create_engine(settings.DATABASE_URL, **engine_options)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
