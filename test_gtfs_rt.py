#!/usr/bin/env python3
"""Test script for GTFS-RT ingestor."""

import asyncio
import sys
from pathlib import Path

# Add src to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from mbta_pipeline.ingestion.gtfs_rt_ingestor import GTFSRTIngestor
from mbta_pipeline.config.settings import settings

async def test_gtfs_rt_ingestor():
    """Test the GTFS-RT ingestor."""
    print("🚇 Testing MBTA GTFS-RT Ingestor")
    print(f"GTFS-RT Base URL: {settings.mbta_gtfs_rt_base_url}")
    print()
    
    try:
        # Create ingestor instance
        ingestor = GTFSRTIngestor()
        print("✅ GTFS-RT Ingestor created successfully")
        
        # Test async context manager
        async with ingestor as ing:
            print("✅ Async context manager working")
            
            # Test feed status (before fetching)
            print("\n📊 Initial feed status:")
            status = await ing.get_feed_status()
            for feed_name, feed_status in status.items():
                print(f"  {feed_name}: {feed_status['status']} (no data yet)")
            
            # Test data fetching
            print("\n🔄 Fetching GTFS-RT data...")
            data = await ing.fetch_data()
            
            print(f"✅ Fetched {len(data)} total records")
            
            # Categorize data by type
            vehicle_positions = [d for d in data if 'latitude' in d]
            trip_updates = [d for d in data if 'stop_time_updates' in d]
            alerts = [d for d in data if 'affected_routes' in d]
            
            print(f"  🚌 Vehicle Positions: {len(vehicle_positions)}")
            print(f"  🚉 Trip Updates: {len(trip_updates)}")
            print(f"  ⚠️  Alerts: {len(alerts)}")
            
            # Show feed status after fetching
            print("\n📊 Updated feed status:")
            status = await ing.get_feed_status()
            for feed_name, feed_status in status.items():
                print(f"  {feed_name}: {feed_status['status']} (age: {feed_status['age_minutes']:.1f} min)")
            
            # Test feed freshness validation
            print("\n🔍 Feed freshness validation:")
            validation = await ing.validate_feed_freshness(max_age_minutes=15)
            for feed_name, is_fresh in validation.items():
                status_icon = "✅" if is_fresh else "❌"
                print(f"  {feed_name}: {status_icon} {'Fresh' if is_fresh else 'Stale'}")
            
            # Show sample data if available
            if vehicle_positions:
                print(f"\n🚌 Sample Vehicle Position:")
                sample = vehicle_positions[0]
                print(f"  Vehicle ID: {sample.get('vehicle_id', 'N/A')}")
                print(f"  Location: ({sample.get('latitude', 'N/A')}, {sample.get('longitude', 'N/A')})")
                print(f"  Route: {sample.get('route_id', 'N/A')}")
                print(f"  Timestamp: {sample.get('timestamp', 'N/A')}")
            
            if trip_updates:
                print(f"\n🚉 Sample Trip Update:")
                sample = trip_updates[0]
                print(f"  Trip ID: {sample.get('trip_id', 'N/A')}")
                print(f"  Route: {sample.get('route_id', 'N/A')}")
                print(f"  Delay: {sample.get('delay', 'N/A')} seconds")
                print(f"  Stop Updates: {len(sample.get('stop_time_updates', []))}")
            
            if alerts:
                print(f"\n⚠️  Sample Alert:")
                sample = alerts[0]
                print(f"  Alert ID: {sample.get('alert_id', 'N/A')}")
                print(f"  Header: {sample.get('alert_header_text', 'N/A')}")
                print(f"  Affected Routes: {len(sample.get('affected_routes', []))}")
                print(f"  Affected Stops: {len(sample.get('affected_stops', []))}")
            
            # Test health check
            print("\n🏥 Health Check:")
            health = await ing.health_check()
            print(f"  Status: {health['status']}")
            print(f"  Total Records: {health['total_records_ingested']}")
            print(f"  Total Errors: {health['total_errors']}")
            print(f"  Consecutive Failures: {health['consecutive_failures']}")
            
    except Exception as e:
        print(f"❌ Error testing GTFS-RT ingestor: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n🎉 GTFS-RT Ingestor test completed successfully!")
    return True

if __name__ == "__main__":
    # Run the test
    success = asyncio.run(test_gtfs_rt_ingestor())
    sys.exit(0 if success else 1)
