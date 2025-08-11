#!/usr/bin/env python3
"""Startup script for MBTA Dashboard."""

import asyncio
import os
import sys
from pathlib import Path

# Add src to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

async def main():
    """Main dashboard startup function."""
    print("MBTA Dashboard Startup")
    print("=" * 50)
    
    # Check if .env file exists
    env_file = Path(".env")
    if not env_file.exists():
        print("WARNING: No .env file found!")
        print("Please create a .env file with your database configuration:")
        print("DATABASE_URL=postgresql://mbta_user:mbta_password@localhost:5432/mbta_data")
        print()
        return
    
    # Check if database is accessible
    from dotenv import load_dotenv
    load_dotenv()
    
    print("Environment configuration loaded successfully")
    
    # Test database connection
    print("\nTesting database connection...")
    try:
        from mbta_pipeline.storage.database import DatabaseManager
        
        db_manager = DatabaseManager()
        if db_manager.test_connection():
            print("Database connection successful")
        else:
            print("Database connection failed!")
            print("Make sure PostgreSQL is running with docker-compose up -d")
            return
            
    except Exception as e:
        print(f"Database error: {str(e)}")
        print("Make sure PostgreSQL is running and the database is initialized")
        return
    
    # Start dashboard
    print("\nStarting MBTA Dashboard...")
    try:
        import uvicorn
        
        print("Dashboard will be available at: http://localhost:8000")
        print("Press Ctrl+C to stop")
        
        # Use import string for uvicorn to enable reload
        uvicorn.run(
            "mbta_pipeline.dashboard.app:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info"
        )
        
    except KeyboardInterrupt:
        print("\nDashboard stopped by user")
    except Exception as e:
        print(f"Dashboard error: {str(e)}")
        return

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nGoodbye!")
    except Exception as e:
        print(f"Fatal error: {str(e)}")
        sys.exit(1)
