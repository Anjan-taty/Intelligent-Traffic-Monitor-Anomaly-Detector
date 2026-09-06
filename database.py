import os
import logging
from typing import Generator
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

load_dotenv()

logger = logging.getLogger("traffic_monitor.database")

DATABASE_URL = os.getenv("DATABASE_URL")

# Resilient connection fallback: PostgreSQL if configured, SQLite if not or on failure
if not DATABASE_URL:
    DATABASE_URL = "sqlite:///./traffic_monitor.db"
    logger.info("DATABASE_URL not set in environment. Falling back to local SQLite: traffic_monitor.db")

connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

try:
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        connect_args=connect_args,
        **({"pool_size": 20, "max_overflow": 10} if not DATABASE_URL.startswith("sqlite") else {})
    )
    # Test connection
    with engine.connect() as conn:
        pass
except Exception as e:
    logger.warning(f"Could not connect to configured database ({DATABASE_URL}): {e}. Falling back to SQLite.")
    DATABASE_URL = "sqlite:///./traffic_monitor.db"
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db() -> Generator[Session, None, None]:
    """FastAPI Dependency for database session with automatic lifecycle management."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initializes all database tables registered on Base."""
    import models  # Ensure models are loaded
    Base.metadata.create_all(bind=engine)