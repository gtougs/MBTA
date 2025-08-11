#!/usr/bin/env python3
"""Script to populate the database with sample data for testing the dashboard."""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta
import random

# Add src to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from mbta_pipeline.storage.database import DatabaseManager
from mbta_pipeline.models.database import (
    Route, Stop, Trip, Prediction, VehiclePosition, Alert, Vehicle
)

async def populate_sample_data():
    """Populate the database with sample data."""
    print("🚇 Populating database with sample data...")
    
    try:
        db_manager = DatabaseManager()
        session = db_manager.get_session()
        
        try:
            # Check if we already have data
            existing_routes = session.query(Route).count()
            existing_predictions = session.query(Prediction).count()
            existing_stops = session.query(Stop).count()
            existing_trips = session.query(Trip).count()
            
            print(f"📊 Current database state:")
            print(f"   - Routes: {existing_routes}")
            print(f"   - Stops: {existing_stops}")
            print(f"   - Trips: {existing_trips}")
            print(f"   - Predictions: {existing_predictions}")
            
            # Only populate if we're missing key data
            if existing_predictions > 0 and existing_stops > 0 and existing_trips > 0:
                print("✅ Database already has sufficient data, skipping population")
                return
            
            print("📊 Creating sample routes...")
            routes = [
                Route(id="Red", route_name="Red Line", route_type=1, route_color="DA291C", route_text_color="FFFFFF"),
                Route(id="Blue", route_name="Blue Line", route_type=1, route_color="003DA5", route_text_color="FFFFFF"),
                Route(id="Green-B", route_name="Green Line B", route_type=0, route_color="00843D", route_text_color="FFFFFF"),
                Route(id="Green-C", route_name="Green Line C", route_type=0, route_color="00843D", route_text_color="FFFFFF"),
                Route(id="Green-D", route_name="Green Line D", route_type=0, route_color="00843D", route_text_color="FFFFFF"),
                Route(id="Green-E", route_name="Green Line E", route_type=0, route_color="00843D", route_text_color="FFFFFF"),
                Route(id="Orange", route_name="Orange Line", route_type=1, route_color="ED8B00", route_text_color="FFFFFF"),
                Route(id="Silver", route_name="Silver Line", route_type=3, route_color="7C878E", route_text_color="FFFFFF"),
            ]
            
            for route in routes:
                session.add(route)
            session.flush()
            
            print("🛑 Creating sample stops...")
            stops = [
                Stop(id="place-pktrm", stop_name="Park Street", stop_lat=42.3564, stop_lon=-71.0624),
                Stop(id="place-dwnxg", stop_name="Downtown Crossing", stop_lat=42.3555, stop_lon=-71.0604),
                Stop(id="place-state", stop_name="State Street", stop_lat=42.3589, stop_lon=-71.0576),
            ]
            
            for stop in stops:
                session.add(stop)
            session.flush()
            
            print("🚂 Creating sample trips...")
            trips = [
                Trip(id="trip_red_1", route_id="Red", service_id="weekday", trip_headsign="Alewife", direction_id=0),
                Trip(id="trip_red_2", route_id="Red", service_id="weekday", trip_headsign="Ashmont", direction_id=1),
                Trip(id="trip_blue_1", route_id="Blue", service_id="weekday", trip_headsign="Wonderland", direction_id=0),
                Trip(id="trip_blue_2", route_id="Blue", service_id="weekday", trip_headsign="Bowdoin", direction_id=1),
            ]
            
            for trip in trips:
                session.add(trip)
            session.flush()
            
            print("⏰ Creating sample predictions...")
            now = datetime.utcnow()
            predictions = []
            
            for i in range(50):  # Create 50 sample predictions
                # Random delay between -300 (5 min early) and 600 (10 min late) seconds
                delay = random.randint(-300, 600)
                # Make arrival times more unique by adding seconds and using different base times
                base_minutes = random.randint(1, 30)
                base_seconds = random.randint(0, 59)
                arrival_time = now + timedelta(minutes=base_minutes, seconds=base_seconds)
                
                prediction = Prediction(
                    trip_id=random.choice(trips).id,
                    route_id=random.choice(routes).id,
                    stop_id=random.choice(stops).id,
                    arrival_time=arrival_time,
                    departure_time=arrival_time + timedelta(minutes=2),
                    delay=delay,
                    timestamp=now - timedelta(minutes=random.randint(0, 60))
                )
                predictions.append(prediction)
            
            for prediction in predictions:
                session.add(prediction)
            session.flush()
            
            print("🚌 Creating sample vehicles...")
            vehicles = []
            for i in range(20):  # Create 20 sample vehicles
                vehicle = Vehicle(
                    id=f"vehicle_{i+1}",
                    vehicle_id=f"vehicle_{i+1}",
                    vehicle_label=f"Vehicle {i+1}",
                    vehicle_type=random.randint(0, 3)  # 0=tram, 1=subway, 2=rail, 3=bus
                )
                vehicles.append(vehicle)
            
            for vehicle in vehicles:
                session.add(vehicle)
            session.flush()
            
            print("🚗 Creating sample vehicle positions...")
            vehicle_positions = []
            
            for i in range(20):  # Create 20 sample vehicle positions
                position = VehiclePosition(
                    vehicle_id=f"vehicle_{i+1}",
                    trip_id=random.choice(trips).id,
                    route_id=random.choice(routes).id,
                    latitude=42.35 + random.uniform(-0.1, 0.1),  # Around Boston
                    longitude=-71.06 + random.uniform(-0.1, 0.1),
                    timestamp=now - timedelta(minutes=random.randint(0, 30))
                )
                vehicle_positions.append(position)
            
            for position in vehicle_positions:
                session.add(position)
            session.flush()
            
            print("⚠️ Creating sample alerts...")
            alerts = [
                Alert(
                    alert_id="alert_1",
                    alert_header_text="Service Delay",
                    alert_description_text="Red Line experiencing delays due to signal problems",
                    affected_route_ids=["Red"],
                    alert_severity_level="moderate",
                    timestamp=now - timedelta(hours=1)
                ),
                Alert(
                    alert_id="alert_2",
                    alert_header_text="Track Maintenance",
                    alert_description_text="Blue Line single tracking between Airport and Maverick",
                    affected_route_ids=["Blue"],
                    alert_severity_level="low",
                    timestamp=now - timedelta(hours=2)
                )
            ]
            
            for alert in alerts:
                session.add(alert)
            
            # Commit all changes
            session.commit()
            
            print("✅ Sample data populated successfully!")
            print(f"   - {len(routes)} routes")
            print(f"   - {len(stops)} stops")
            print(f"   - {len(trips)} trips")
            print(f"   - {len(predictions)} predictions")
            print(f"   - {len(vehicle_positions)} vehicle positions")
            print(f"   - {len(alerts)} alerts")
            
        except Exception as e:
            session.rollback()
            print(f"❌ Error populating data: {e}")
            raise
        finally:
            session.close()
            
    except Exception as e:
        print(f"❌ Failed to populate sample data: {e}")
        return False
    
    return True

if __name__ == "__main__":
    try:
        success = asyncio.run(populate_sample_data())
        if success:
            print("\n🎉 Database is now populated with sample data!")
            print("The dashboard should now display real metrics instead of placeholder data.")
        else:
            print("\n❌ Failed to populate database.")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n⏹️ Operation cancelled by user")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)
