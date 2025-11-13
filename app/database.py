# app/database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .config import settings


# Create engine using secure DATABASE_URL from .env
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,        # Verify connections
    pool_size=5,
    max_overflow=10,
    echo=False                 # Set to True only in debug
)

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Base class for models
Base = declarative_base()


def get_db():
    """
    Dependency to get DB session.
    Use in routes: db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()