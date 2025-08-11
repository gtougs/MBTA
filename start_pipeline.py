#!/usr/bin/env python3
"""Startup script for MBTA Data Pipeline."""

import asyncio
import os
import sys
from pathlib import Path

# Add src to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

async def main():
    """Main startup function."""
    print("MBTA Data Pipeline Startup")
    print("=" * 50)
    
    # Check if .env file exists
    env_file = Path(".env")
    if not env_file.exists():
        print("WARNING: No .env file found!")
        print("Please create a .env file with your MBTA API key:")
        print("MBTA_API_KEY=your_api_key_here")
        print()
        print("You can copy from .env.example if it exists")
        return
    
    # Check if MBTA API key is set
    from dotenv import load_dotenv
    load_dotenv()
    
    api_key = os.getenv("MBTA_API_KEY")
    if not api_key or api_key == "your_mbta_api_key_here":
        print("ERROR: MBTA API key not set!")
        print("Please set MBTA_API_KEY in your .env file")
        return
    
    print("Environment configuration looks good")
    
    # Initialize database
    print("\nInitializing database...")
    try:
        from mbta_pipeline.storage.init_database import initialize_database, verify_database
        
        success = await initialize_database()
        if not success:
            print("Database initialization failed!")
            return
        
        print("Database initialized successfully")
        
        # Verify database
        status = await verify_database()
        print(f"Database status: {status['status']}")
        print(f"Tables: {status['table_counts']}")
        
    except Exception as e:
        print(f"Database error: {str(e)}")
        print("Make sure PostgreSQL is running with docker-compose up -d")
        return
    
    # Start pipeline
    print("\nStarting MBTA Data Pipeline...")
    try:
        from main import main as run_pipeline
        await run_pipeline()
    except KeyboardInterrupt:
        print("\nPipeline stopped by user")
    except Exception as e:
        print(f"Pipeline error: {str(e)}")
        return

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nGoodbye!")
    except Exception as e:
        print(f"Fatal error: {str(e)}")
        sys.exit(1)
