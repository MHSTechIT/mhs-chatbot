import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
import logging

logger = logging.getLogger(__name__)

# Use Supabase PostgreSQL database
DATABASE_URL = os.getenv("DB_CONNECTION", "sqlite:///fallback.db")

# Lazy-load the engine to avoid connection errors on startup
_engine = None
_SessionLocal = None

def _get_engine():
    global _engine
    if _engine is None:
        try:
            _engine = create_engine(
                DATABASE_URL,
                pool_pre_ping=True,
                pool_recycle=3600,
                echo=False,
                connect_args={"timeout": 5} if "sqlite" in DATABASE_URL else {},
            )
            logger.info("✅ Database connection initialized")
        except Exception as e:
            logger.warning(f"⚠️ Database connection failed: {str(e)}")
    return _engine

def _get_session_local():
    global _SessionLocal
    if _SessionLocal is None:
        engine = _get_engine()
        if engine:
            _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return _SessionLocal

Base = declarative_base()

def get_db():
    """Dependency for getting database session."""
    SessionLocal = _get_session_local()
    if SessionLocal:
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

def init_db():
    """Initialize database tables."""
    engine = _get_engine()
    if engine:
        try:
            Base.metadata.create_all(bind=engine)
            logger.info("✅ Database tables created successfully")
        except Exception as e:
            logger.warning(f"⚠️ Failed to create database tables: {str(e)}")
    else:
        logger.warning("⚠️ Skipping database table creation - no database connection available")

class SessionLocal:
    """Lazy-loaded SessionLocal factory for backward compatibility."""
    def __new__(cls):
        SessionFactory = _get_session_local()
        if SessionFactory:
            return SessionFactory()
        else:
            raise RuntimeError("Database connection not available. Cannot create session.")
