"""Database connection and session management for MBTA pipeline storage."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from contextlib import contextmanager
from typing import Generator
import logging

from ..config.settings import settings

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database connections and sessions."""
    
    def __init__(self):
        self.engine = None
        self.SessionLocal = None
        self._initialize_engine()
    
    def _initialize_engine(self):
        """Initialize the SQLAlchemy engine with connection pooling."""
        try:
            # Create engine with connection pooling
            self.engine = create_engine(
                settings.database_url,
                poolclass=QueuePool,
                pool_size=getattr(settings, 'database_pool_size', 5),
                max_overflow=getattr(settings, 'database_max_overflow', 10),
                pool_pre_ping=True,  # Verify connections before use
                pool_recycle=3600,   # Recycle connections every hour
                echo=getattr(settings, 'database_echo', False),  # SQL logging in development
            )
            
            # Create session factory
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )
            
            logger.info("Database engine initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database engine: {e}")
            raise
    
    def get_session(self) -> Session:
        """Get a new database session."""
        if not self.SessionLocal:
            raise RuntimeError("Database not initialized")
        return self.SessionLocal()
    
    @contextmanager
    def get_session_context(self) -> Generator[Session, None, None]:
        """Context manager for database sessions with automatic cleanup."""
        session = self.get_session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    async def get_session_async(self) -> Session:
        """Get a database session for async operations."""
        return self.get_session()
    
    async def close_session_async(self, session: Session) -> None:
        """Close a database session for async operations."""
        try:
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    def test_connection(self) -> bool:
        """Test database connectivity."""
        try:
            with self.engine.connect() as conn:
                from sqlalchemy import text
                result = conn.execute(text("SELECT 1"))
                return result.scalar() == 1
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False
    
    def create_tables(self):
        """Create all tables defined in the models."""
        try:
            from ..models.database import Base
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create database tables: {e}")
            raise
    
    def drop_tables(self):
        """Drop all tables (use with caution!)."""
        try:
            from ..models.database import Base
            Base.metadata.drop_all(bind=self.engine)
            logger.warning("Database tables dropped successfully")
        except Exception as e:
            logger.error(f"Failed to drop database tables: {e}")
            raise
    
    def close(self):
        """Close all database connections."""
        if self.engine:
            self.engine.dispose()
            logger.info("Database connections closed")


# Global database manager instance
db_manager = DatabaseManager()


def get_db() -> Session:
    """Dependency function to get database session."""
    return db_manager.get_session()


def get_db_context():
    """Dependency function to get database session context."""
    return db_manager.get_session_context()


async def get_db_async() -> Session:
    """Async dependency function to get database session."""
    return await db_manager.get_session_async()


async def close_db_async(session: Session) -> None:
    """Async function to close database session."""
    await db_manager.close_session_async(session)
