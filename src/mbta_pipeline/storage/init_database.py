"""Database initialization script for MBTA transit data."""

import asyncio
import logging
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
from typing import Dict, Any

from .database import DatabaseManager
from ..models.database import Base
from ..config.settings import settings

logger = logging.getLogger(__name__)


class DatabaseInitializer:
    """Handles database initialization and table creation."""
    
    def __init__(self):
        """Initialize the database initializer."""
        self.db_manager = DatabaseManager()
    
    async def initialize_database(self) -> bool:
        """Initialize the database and create all tables."""
        try:
            logger.info("Starting database initialization...")
            
            # Test database connection
            if not self.db_manager.test_connection():
                logger.error("Database connection test failed")
                return False
            
            logger.info("Database connection successful")
            
            # Create all tables
            await self._create_tables()
            
            # Create indexes for performance
            await self._create_indexes()
            
            # Insert initial reference data
            await self._insert_initial_data()
            
            logger.info("Database initialization completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Database initialization failed: {str(e)}", exc_info=True)
            return False
    
    async def _create_tables(self) -> None:
        """Create all database tables."""
        try:
            logger.info("Creating database tables...")
            
            # Create all tables defined in models
            Base.metadata.create_all(bind=self.db_manager.engine)
            
            logger.info("All tables created successfully")
            
        except Exception as e:
            logger.error(f"Failed to create tables: {str(e)}")
            raise
    
    async def _create_indexes(self) -> None:
        """Create additional indexes for performance."""
        try:
            logger.info("Creating performance indexes...")
            
            session = self.db_manager.get_session()
            try:
                # Create composite indexes for common query patterns
                indexes = [
                    # Predictions table indexes
                    "CREATE INDEX IF NOT EXISTS idx_predictions_route_time ON predictions (route_id, timestamp)",
                    "CREATE INDEX IF NOT EXISTS idx_predictions_stop_time ON predictions (stop_id, timestamp)",
                    "CREATE INDEX IF NOT EXISTS idx_predictions_trip_time ON predictions (trip_id, timestamp)",
                    "CREATE INDEX IF NOT EXISTS idx_predictions_delay ON predictions (delay) WHERE delay > 0",
                    
                    # Vehicle positions table indexes
                    "CREATE INDEX IF NOT EXISTS idx_vehicle_positions_route_time ON vehicle_positions (route_id, timestamp)",
                    "CREATE INDEX IF NOT EXISTS idx_vehicle_positions_vehicle_time ON vehicle_positions (vehicle_id, timestamp)",
                    "CREATE INDEX IF NOT EXISTS idx_vehicle_positions_location ON vehicle_positions (latitude, longitude)",
                    
                    # Trip updates table indexes
                    "CREATE INDEX IF NOT EXISTS idx_trip_updates_trip_time ON trip_updates (trip_id, timestamp)",
                    "CREATE INDEX IF NOT EXISTS idx_trip_updates_route_time ON trip_updates (route_id, timestamp)",
                    
                    # Alerts table indexes
                    "CREATE INDEX IF NOT EXISTS idx_alerts_severity_time ON alerts (alert_severity_level, timestamp)",
                    "CREATE INDEX IF NOT EXISTS idx_alerts_effect_time ON alerts (alert_effect, timestamp)",
                    
                    # Data ingestion logs indexes
                    "CREATE INDEX IF NOT EXISTS idx_ingestion_logs_source_time ON data_ingestion_logs (source_type, started_at)",
                    "CREATE INDEX IF NOT EXISTS idx_ingestion_logs_status_time ON data_ingestion_logs (status, started_at)"
                ]
                
                for index_sql in indexes:
                    try:
                        session.execute(text(index_sql))
                        session.commit()
                    except SQLAlchemyError as e:
                        logger.warning(f"Index creation warning (may already exist): {str(e)}")
                        session.rollback()
                
                logger.info("Performance indexes created successfully")
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Failed to create indexes: {str(e)}")
            raise
    
    async def _insert_initial_data(self) -> None:
        """Insert initial reference data."""
        try:
            logger.info("Inserting initial reference data...")
            
            session = self.db_manager.get_session()
            try:
                # Check if we already have data
                from ..models.database import Route
                existing_routes = session.query(Route).count()
                
                if existing_routes > 0:
                    logger.info("Reference data already exists, skipping insertion")
                    return
                
                # Insert basic MBTA route information
                routes_data = [
                    {
                        'id': 'Red',
                        'route_name': 'Red Line',
                        'route_type': 1,  # Subway
                        'route_color': 'DA291C',
                        'route_text_color': 'FFFFFF',
                        'route_sort_order': 1,
                        'route_long_name': 'Red Line Subway',
                        'route_desc': 'Rapid transit service between Alewife and Ashmont/Braintree'
                    },
                    {
                        'id': 'Orange',
                        'route_name': 'Orange Line',
                        'route_type': 1,  # Subway
                        'route_color': 'FF8C00',
                        'route_text_color': 'FFFFFF',
                        'route_sort_order': 2,
                        'route_long_name': 'Orange Line Subway',
                        'route_desc': 'Rapid transit service between Oak Grove and Forest Hills'
                    },
                    {
                        'id': 'Blue',
                        'route_name': 'Blue Line',
                        'route_type': 1,  # Subway
                        'route_color': '003DA5',
                        'route_text_color': 'FFFFFF',
                        'route_sort_order': 3,
                        'route_long_name': 'Blue Line Subway',
                        'route_desc': 'Rapid transit service between Wonderland and Bowdoin'
                    },
                    {
                        'id': 'Green-B',
                        'route_name': 'Green Line B',
                        'route_type': 0,  # Light rail
                        'route_color': '00843D',
                        'route_text_color': 'FFFFFF',
                        'route_sort_order': 4,
                        'route_long_name': 'Green Line B Branch',
                        'route_desc': 'Light rail service between Government Center and Boston College'
                    },
                    {
                        'id': 'Green-C',
                        'route_name': 'Green Line C',
                        'route_type': 0,  # Light rail
                        'route_color': '00843D',
                        'route_text_color': 'FFFFFF',
                        'route_sort_order': 5,
                        'route_long_name': 'Green Line C Branch',
                        'route_desc': 'Light rail service between Government Center and Cleveland Circle'
                    },
                    {
                        'id': 'Green-D',
                        'route_name': 'Green Line D',
                        'route_type': 0,  # Light rail
                        'route_color': '00843D',
                        'route_text_color': 'FFFFFF',
                        'route_sort_order': 6,
                        'route_long_name': 'Green Line D Branch',
                        'route_desc': 'Light rail service between Government Center and Riverside'
                    },
                    {
                        'id': 'Green-E',
                        'route_name': 'Green Line E',
                        'route_type': 0,  # Light rail
                        'route_color': '00843D',
                        'route_text_color': 'FFFFFF',
                        'route_sort_order': 7,
                        'route_long_name': 'Green Line E Branch',
                        'route_desc': 'Light rail service between Government Center and Heath Street'
                    },
                    {
                        'id': 'CR-Fairmount',
                        'route_name': 'Fairmount Line',
                        'route_type': 2,  # Commuter rail
                        'route_color': '000000',
                        'route_text_color': 'FFFFFF',
                        'route_sort_order': 8,
                        'route_long_name': 'Fairmount Commuter Rail Line',
                        'route_desc': 'Commuter rail service between South Station and Readville'
                    }
                ]
                
                for route_data in routes_data:
                    route = Route(**route_data)
                    session.add(route)
                
                session.commit()
                logger.info(f"Inserted {len(routes_data)} initial routes")
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Failed to insert initial data: {str(e)}")
            raise
    
    async def verify_database(self) -> Dict[str, Any]:
        """Verify database setup and return status."""
        try:
            session = self.db_manager.get_session()
            try:
                # Check table counts
                table_counts = {}
                tables = ['routes', 'stops', 'trips', 'predictions', 'vehicle_positions', 'trip_updates', 'alerts']
                
                for table in tables:
                    try:
                        result = session.execute(text(f"SELECT COUNT(*) FROM {table}"))
                        count = result.scalar()
                        table_counts[table] = count
                    except SQLAlchemyError:
                        table_counts[table] = 0
                
                # Check database size
                db_size_result = session.execute(text("""
                    SELECT pg_size_pretty(pg_database_size(current_database())) as db_size
                """))
                db_size = db_size_result.scalar()
                
                # Check connection pool status
                pool_status = {
                    'pool_size': self.db_manager.engine.pool.size(),
                    'checked_in': self.db_manager.engine.pool.checkedin(),
                    'checked_out': self.db_manager.engine.pool.checkedout(),
                    'overflow': self.db_manager.engine.pool.overflow()
                }
                
                return {
                    'status': 'healthy',
                    'table_counts': table_counts,
                    'database_size': db_size,
                    'connection_pool': pool_status,
                    'timestamp': str(datetime.utcnow())
                }
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Database verification failed: {str(e)}")
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': str(datetime.utcnow())
            }
    
    async def reset_database(self) -> bool:
        """Reset the database by dropping all tables and recreating them."""
        try:
            logger.warning("Resetting database - this will delete all data!")
            
            # Drop all tables
            Base.metadata.drop_all(bind=self.db_manager.engine)
            logger.info("All tables dropped")
            
            # Recreate tables
            await self._create_tables()
            await self._create_indexes()
            await self._insert_initial_data()
            
            logger.info("Database reset completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Database reset failed: {str(e)}")
            return False


# Global initializer instance
db_initializer = DatabaseInitializer()


async def initialize_database() -> bool:
    """Initialize the database."""
    return await db_initializer.initialize_database()


async def verify_database() -> Dict[str, Any]:
    """Verify database setup."""
    return await db_initializer.verify_database()


async def reset_database() -> bool:
    """Reset the database."""
    return await db_initializer.reset_database()


if __name__ == "__main__":
    # Run database initialization
    async def main():
        success = await initialize_database()
        if success:
            status = await verify_database()
            print(f"Database status: {status}")
        else:
            print("Database initialization failed")
    
    asyncio.run(main())
