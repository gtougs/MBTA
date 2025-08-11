#!/usr/bin/env python3
"""Test script for aggregator to storage integration."""

import asyncio
import sys
import os
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from mbta_pipeline.processing.aggregator import DataAggregator
from mbta_pipeline.storage.transit_storage import transit_storage
from mbta_pipeline.models.transit import Prediction, VehiclePosition, Alert
from mbta_pipeline.config.settings import settings


async def test_storage_integration():
    """Test the aggregator to storage integration."""
    print("🚀 Testing Aggregator to Storage Integration")
    print("=" * 50)
    
    # Initialize aggregator
    aggregator = DataAggregator()
    print("✅ Aggregator initialized")
    
    # Test data
    test_prediction = Prediction(
        prediction_id="test_pred_001",
        trip_id="test_trip_001",
        stop_id="test_stop_001",
        route_id="test_route_001",
        arrival_time=datetime.utcnow() + timedelta(minutes=5),
        departure_time=datetime.utcnow() + timedelta(minutes=6),
        schedule_relationship="scheduled",
        vehicle_id="test_vehicle_001",
        vehicle_label="Test Vehicle",
        status="on_time",
        delay=0,
        source="test"
    )
    
    test_vehicle_position = VehiclePosition(
        vehicle_id="test_vehicle_001",
        trip_id="test_trip_001",
        route_id="test_route_001",
        latitude=42.3601,
        longitude=-71.0589,
        bearing=90.0,
        speed=15.0,
        current_status="in_transit",
        timestamp=datetime.utcnow(),
        congestion_level="low",
        occupancy_status="many_seats_available",
        source="test"
    )
    
    test_alert = Alert(
        alert_id="test_alert_001",
        alert_header_text="Test Alert",
        alert_description_text="This is a test alert for testing purposes",
        alert_url="https://example.com/test",
        effective_start_date=datetime.utcnow(),
        effective_end_date=datetime.utcnow() + timedelta(hours=1),
        affected_routes=["test_route_001"],
        affected_stops=["test_stop_001"],
        affected_trips=["test_trip_001"],
        alert_severity_level="minor",
        cause="testing",
        effect="delays",
        source="test"
    )
    
    print("✅ Test data created")
    
    # Test individual processing and storage
    print("\n📊 Testing individual data processing and storage...")
    
    try:
        # Process and store prediction
        result = await aggregator.process_and_store(test_prediction)
        print(f"Prediction storage: {'✅' if result['success'] else '❌'} {result}")
        
        # Process and store vehicle position
        result = await aggregator.process_and_store(test_vehicle_position)
        print(f"Vehicle position storage: {'✅' if result['success'] else '❌'} {result}")
        
        # Process and store alert
        result = await aggregator.process_and_store(test_alert)
        print(f"Alert storage: {'✅' if result['success'] else '❌'} {result}")
        
    except Exception as e:
        print(f"❌ Storage test failed: {str(e)}")
        return
    
    # Test batch processing
    print("\n📦 Testing batch processing...")
    
    try:
        batch_result = await aggregator.process_batch(
            [test_prediction, test_vehicle_position, test_alert],
            source_type="test_batch"
        )
        print(f"Batch processing: {'✅' if batch_result['success'] else '❌'} {batch_result}")
        
    except Exception as e:
        print(f"❌ Batch processing test failed: {str(e)}")
    
    # Test aggregation summary storage
    print("\n📈 Testing aggregation summary storage...")
    
    try:
        summary_result = await aggregator.store_aggregation_summary()
        print(f"Summary storage: {'✅' if summary_result['success'] else '❌'} {summary_result}")
        
    except Exception as e:
        print(f"❌ Summary storage test failed: {str(e)}")
    
    # Test retrieving stored data
    print("\n🔍 Testing data retrieval...")
    
    try:
        recent_predictions = await aggregator.get_stored_recent_predictions(limit=10)
        print(f"Recent predictions: {'✅' if recent_predictions else '❌'} Found {len(recent_predictions)} records")
        
        service_health = await aggregator.get_stored_service_health(hours=1)
        print(f"Service health: {'✅' if 'error' not in service_health else '❌'} {service_health}")
        
    except Exception as e:
        print(f"❌ Data retrieval test failed: {str(e)}")
    
    # Get aggregator statistics
    print("\n📊 Aggregator Statistics:")
    summary = aggregator.get_summary_stats()
    print(f"Total records: {summary['total_records']}")
    print(f"By type: {summary['by_type']}")
    
    route_summary = aggregator.get_route_summary()
    print(f"Route summary: {len(route_summary)} routes")
    
    service_health = aggregator.get_service_health_summary()
    print(f"Service health: {service_health['service_status']}")
    print(f"Delay percentage: {service_health['delay_percentage']}%")
    
    print("\n🎉 Storage integration test completed!")


if __name__ == "__main__":
    # Check if we have required environment variables
    if not hasattr(settings, 'database_url'):
        print("❌ Database URL not configured. Please check your environment variables.")
        print("Expected: DATABASE_URL or database configuration in settings")
        sys.exit(1)
    
    print(f"🔗 Using database: {settings.database_url}")
    
    # Run the test
    asyncio.run(test_storage_integration())
