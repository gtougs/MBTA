#!/usr/bin/env python3
"""Demo script for aggregator to storage integration."""

import asyncio
import sys
import os
from datetime import datetime, timedelta, timezone

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Ensure required env for settings is present before importing modules that load settings
if "MBTA_API_KEY" not in os.environ:
    os.environ["MBTA_API_KEY"] = "demo"

from mbta_pipeline.processing.aggregator import DataAggregator
from mbta_pipeline.models.transit import Prediction, VehiclePosition, Alert, Route, Stop, Trip
from mbta_pipeline.config.settings import settings
from mbta_pipeline.storage.database import db_manager
from mbta_pipeline.storage.transit_storage import transit_storage


async def demo_aggregator_storage():
    """Demo the aggregator with storage capabilities, including optional DB write/read."""
    print("🚀 MBTA Pipeline - Aggregator to Storage Demo")
    print("=" * 50)

    # Initialize aggregator
    aggregator = DataAggregator()
    print("✅ Aggregator initialized")

    # Show database URL (masked)
    db_url = getattr(settings, 'database_url', 'unset')
    print(f"🔗 Database URL: {db_url}")

    # Check DB connectivity
    storage_available = False
    try:
        if db_manager.test_connection():
            print("✅ Database connection OK")
            try:
                db_manager.create_tables()
                print("✅ Database tables ensured")
            except Exception as e:
                print(f"⚠️ Could not ensure tables: {e}")
            storage_available = True
        else:
            print("⚠️ Database connection failed; continuing without storage")
    except Exception as e:
        print(f"⚠️ Database check error: {e}")

    # If storage is available, pre-seed minimal entities to satisfy FKs
    if storage_available:
        try:
            # Seed a route/stop/trip that match our first sample records
            await transit_storage.store_transit_data(
                Route(route_id="route_001", route_name="Route 001", route_type=1, source="demo"),
                source_type="demo_seed",
            )
            await transit_storage.store_transit_data(
                Stop(stop_id="stop_001", stop_name="Stop 001", source="demo"),
                source_type="demo_seed",
            )
            await transit_storage.store_transit_data(
                Trip(trip_id="trip_001", route_id="route_001", service_id="svc_demo", source="demo"),
                source_type="demo_seed",
            )
            print("✅ Seeded demo Route/Stop/Trip for storage tests")
        except Exception as e:
            print(f"⚠️ Seeding minimal entities failed: {e}")

    # Create sample transit data
    print("\n📊 Creating sample transit data...")

    predictions = [
        Prediction(
            prediction_id=f"pred_{i:03d}",
            trip_id=f"trip_{i:03d}",
            stop_id=f"stop_{i:03d}",
            route_id=f"route_{i:03d}",
            arrival_time=datetime.now(timezone.utc) + timedelta(minutes=i * 5),
            departure_time=datetime.now(timezone.utc) + timedelta(minutes=i * 5 + 1),
            schedule_relationship="scheduled",
            vehicle_id=f"vehicle_{i:03d}",
            vehicle_label=f"Vehicle {i:03d}",
            status="on_time" if i % 2 == 0 else "delayed",
            delay=0 if i % 2 == 0 else i * 30,
            source="demo",
        )
        for i in range(1, 6)
    ]

    vehicle_positions = [
        VehiclePosition(
            vehicle_id=f"vehicle_{i:03d}",
            trip_id=f"trip_{i:03d}",
            route_id=f"route_{i:03d}",
            latitude=42.3601 + (i * 0.001),
            longitude=-71.0589 + (i * 0.001),
            bearing=90.0 + (i * 10),
            speed=15.0 + (i * 2),
            current_status="in_transit",
            timestamp=datetime.now(timezone.utc),
            congestion_level="low",
            occupancy_status="many_seats_available",
            source="demo",
        )
        for i in range(1, 4)
    ]

    alerts = [
        Alert(
            alert_id=f"alert_{i:03d}",
            alert_header_text=f"Demo Alert {i}",
            alert_description_text=f"This is demo alert {i} for testing purposes",
            alert_url="https://example.com/demo",
            effective_start_date=datetime.now(timezone.utc),
            effective_end_date=datetime.now(timezone.utc) + timedelta(hours=i),
            affected_routes=[f"route_{i:03d}"],
            affected_stops=[f"stop_{i:03d}"],
            affected_trips=[f"trip_{i:03d}"],
            alert_severity_level="minor" if i % 2 == 0 else "major",
            cause="demo",
            effect="delays",
            source="demo",
        )
        for i in range(1, 3)
    ]

    print(
        f"✅ Created {len(predictions)} predictions, {len(vehicle_positions)} vehicle positions, {len(alerts)} alerts"
    )

    # Process data through aggregator
    print("\n🔄 Processing data through aggregator...")

    for prediction in predictions:
        aggregator.process(prediction)

    for position in vehicle_positions:
        aggregator.process(position)

    for alert in alerts:
        aggregator.process(alert)

    print("✅ Data processed through aggregator")

    # Get aggregation statistics
    print("\n📈 Aggregation Statistics:")
    summary = aggregator.get_summary_stats()
    print(f"Total records: {summary['total_records']}")
    print(f"By type: {summary['by_type']}")

    # Get route summary
    route_summary = aggregator.get_route_summary()
    print(f"\n🚌 Route Summary ({len(route_summary)} routes):")
    for route_id, stats in list(route_summary.items())[:3]:  # Show first 3 routes
        print(
            f"  {route_id}: {stats['predictions']} predictions, {stats['vehicle_positions']} positions, {stats['alerts']} alerts"
        )

    # Get service health summary
    service_health = aggregator.get_service_health_summary()
    print(f"\n🏥 Service Health:")
    print(f"  Status: {service_health['service_status']}")
    print(f"  Delay Percentage: {service_health['delay_percentage']}%")
    print(f"  Total Alerts: {service_health['total_alerts']}")

    # If storage available, exercise write/read
    if storage_available:
        print("\n💾 Testing storage integration...")
        try:
            # Individual stores
            result = await aggregator.process_and_store(predictions[0])
            print(f"  Prediction store: {'✅' if result.get('success') else '❌'} {result}")

            result = await aggregator.process_and_store(vehicle_positions[0])
            print(f"  Vehicle position store: {'✅' if result.get('success') else '❌'} {result}")

            result = await aggregator.process_and_store(alerts[0])
            print(f"  Alert store: {'✅' if result.get('success') else '❌'} {result}")

            # Batch store (use only pre-seeded IDs to avoid FK issues)
            batch = [predictions[0], vehicle_positions[0], alerts[0]]
            batch_result = await aggregator.process_batch(batch, source_type="demo_batch")
            print(
                f"  Batch store: {'✅' if batch_result.get('success') else '❌'} {batch_result}"
            )

            # Store aggregation summary (sanitize datetimes for JSON column)
            def _sanitize(obj):
                import datetime as _dt
                if isinstance(obj, dict):
                    return {k: _sanitize(v) for k, v in obj.items()}
                if isinstance(obj, list):
                    return [_sanitize(v) for v in obj]
                if isinstance(obj, (_dt.datetime, _dt.date)):
                    return obj.isoformat()
                return obj

            sanitized_summary = _sanitize(summary)
            summary_result = await transit_storage.store_aggregation_summary(sanitized_summary)
            print(
                f"  Summary store: {'✅' if summary_result.get('success') else '❌'} {summary_result}"
            )

            # Retrievals
            recent_predictions = await aggregator.get_stored_recent_predictions(limit=5)
            print(
                f"  Recent predictions: {'✅' if isinstance(recent_predictions, list) else '❌'} count={len(recent_predictions) if isinstance(recent_predictions, list) else 'n/a'}"
            )
            stored_health = await aggregator.get_stored_service_health(hours=1)
            print(
                f"  Stored service health: {'✅' if 'error' not in stored_health else '❌'} {stored_health}"
            )
        except Exception as e:
            print(f"❌ Storage integration error: {e}")
    else:
        print("\nℹ️ Storage not available. To test full integration:")
        print("   - Start PostgreSQL (see docker-compose.yml)")
        print("   - Export DATABASE_URL pointing to your DB")
        print("   - Re-run this script")

    # Show aggregator configuration
    print(f"\n⚙️ Aggregator Configuration:")
    print(f"  Storage enabled: {aggregator.storage_enabled}")
    print(f"  Batch size: {aggregator.batch_size}")

    print("\n🎉 Demo completed!")


if __name__ == "__main__":
    asyncio.run(demo_aggregator_storage())
