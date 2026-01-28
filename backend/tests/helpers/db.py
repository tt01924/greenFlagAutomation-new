"""Database test helpers for setting up and tearing down test databases."""
import logging
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from src.models.base import Base

logger = logging.getLogger(__name__)

# Use in-memory SQLite for tests
TEST_DATABASE_URL = "sqlite:///:memory:"


def get_test_db_engine():
    """Create test database engine.

    Returns:
        SQLAlchemy engine for testing
    """
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    return engine


def create_test_db() -> Session:
    """Create test database with all tables.

    Returns:
        Test database session
    """
    engine = get_test_db_engine()

    # Create all tables
    Base.metadata.create_all(bind=engine)

    # Create session
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestSessionLocal()

    logger.info("Created test database")
    return db


def drop_test_db(db: Session) -> None:
    """Drop test database and close session.

    Args:
        db: Test database session
    """
    try:
        db.close()
        engine = db.get_bind()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
        logger.info("Dropped test database")
    except Exception as e:
        logger.error(f"Error dropping test database: {e}")


def get_test_db_session() -> Generator[Session, None, None]:
    """Get test database session (for use with FastAPI dependency override).

    Yields:
        Test database session
    """
    db = create_test_db()
    try:
        yield db
    finally:
        drop_test_db(db)


def seed_test_data(db: Session) -> None:
    """Seed test database with sample data.

    Args:
        db: Test database session
    """
    from src.models.system_config import SystemConfig

    # Create system config
    system_config = SystemConfig(
        id=1,
        automation_enabled=True,
        shadow_mode_active=False,
    )
    db.add(system_config)
    db.commit()

    logger.info("Seeded test database")
