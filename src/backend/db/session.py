"""Database Connection & Session Management."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from loguru import logger

from ...config import settings
from .models import Base

# SQLite thread support or PostgreSQL pool
connect_args = {"check_same_thread": False} if "sqlite" in settings.database_url else {}

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Initializes tables in database."""
    Base.metadata.create_all(bind=engine)
    logger.info(f"Database initialized with URL: {settings.database_url}")


def get_db():
    """FastAPI Dependency for database session management."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
