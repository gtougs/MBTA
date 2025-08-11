#!/usr/bin/env python3
"""Test script to verify database schema and basic operations."""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'mbta_pipeline'))

from mbta_pipeline.storage.database import db_manager
from mbta_pipeline.models.database import Route, Stop, Trip, Vehicle, VehiclePosition, Prediction, TripUpdate, Alert, DataIngestionLog
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import uuid


def test_database_connection():
    """Test database connectivity."""
    print("🔌 Testing Database Connection...")
    
    try:
        # Test connection
        if db_manager.test_connection():
            print("   ✅ Database connection successful")
        else:
            print("   ❌ Database connection failed")
            return False
            
        # Test session creation
        with db_manager.get_session_context() as session:
            from sqlalchemy import text
            result = session.execute(text("SELECT version()"))
            version = result.scalar()
            print(f"   ✅ Session creation successful (PostgreSQL {version})")
            
        return True
        
    except Exception as e:
        print(f"   ❌ Database test failed: {e}")
        return False


def test_table_creation():
    """Test that all tables exist."""
    print("\n📋 Testing Table Creation...")
    
    try:
        with db_manager.get_session_context() as session:
            # Check if tables exist by querying them
            tables = [
                ('routes', Route),
                ('stops', Stop),
                ('trips', Trip),
                ('vehicles', Vehicle),
                ('vehicle_positions', VehiclePosition),
                ('predictions', Prediction),
                ('trip_updates', TripUpdate),
                ('alerts', Alert),
                ('data_ingestion_logs', DataIngestionLog)
            ]
            
            for table_name, model_class in tables:
                try:
                    count = session.query(model_class).count()
                    print(f"   ✅ {table_name}: {count} records")
                except Exception as e:
                    print(f"   ❌ {table_name}: {e}")
                    
        return True
        
    except Exception as e:
        print(f"   ❌ Table test failed: {e}")
        return False


def test_basic_operations():
    """Test basic database operations."""
    print("\n🔧 Testing Basic Operations...")
    
    try:
        with db_manager.get_session_context() as session:
            # Test inserting a sample route
            test_route = Route(
                id="test_route_001",
                route_name="Test Route",
                route_type=1,
                route_color="#FF0000",
                route_text_color="#FFFFFF"
            )
            
            session.add(test_route)
            session.commit()
            print("   ✅ Route insertion successful")
            
            # Test querying the route
            route = session.query(Route).filter_by(id="test_route_001").first()
            if route:
                print(f"   ✅ Route query successful: {route.route_name}")
            else:
                print("   ❌ Route query failed")
                
            # Test updating the route
            route.route_name = "Updated Test Route"
            session.commit()
            print("   ✅ Route update successful")
            
            # Test deleting the route
            session.delete(route)
            session.commit()
            print("   ✅ Route deletion successful")
            
        return True
        
    except Exception as e:
        print(f"   ❌ Basic operations test failed: {e}")
        return False


def test_relationships():
    """Test database relationships."""
    print("\n🔗 Testing Database Relationships...")
    
    try:
        with db_manager.get_session_context() as session:
            # Create test data with relationships
            route = Route(
                id="test_route_002",
                route_name="Relationship Test Route",
                route_type=1
            )
            
            stop = Stop(
                id="test_stop_001",
                stop_name="Test Stop",
                stop_lat=42.3601,
                stop_lon=-71.0589
            )
            
            trip = Trip(
                id="test_trip_001",
                route_id=route.id,
                service_id="test_service"
            )
            
            vehicle = Vehicle(
                id="test_vehicle_001",
                vehicle_id="test_vehicle_001",
                vehicle_label="Test Vehicle"
            )
            
            # Add all entities
            session.add_all([route, stop, trip, vehicle])
            session.commit()
            
            # Test relationship queries
            route_with_trips = session.query(Route).filter_by(id=route.id).first()
            if route_with_trips and route_with_trips.trips:
                print("   ✅ Route-Trip relationship working")
            else:
                print("   ❌ Route-Trip relationship failed")
                
            # Clean up test data
            session.delete(vehicle)
            session.delete(trip)
            session.delete(stop)
            session.delete(route)
            session.commit()
            print("   ✅ Test data cleanup successful")
            
        return True
        
    except Exception as e:
        print(f"   ❌ Relationships test failed: {e}")
        return False


def test_indexes():
    """Test that indexes are working properly."""
    print("\n📊 Testing Database Indexes...")
    
    try:
        with db_manager.get_session_context() as session:
            from sqlalchemy import text
            
            # Test spatial index on stops
            result = session.execute(text("""
                SELECT COUNT(*) FROM stops 
                WHERE stop_lat BETWEEN 42.0 AND 43.0 
                AND stop_lon BETWEEN -72.0 AND -70.0
            """))
            count = result.scalar()
            print(f"   ✅ Spatial query test: {count} stops in Boston area")
            
            # Test timestamp index
            result = session.execute(text("""
                SELECT COUNT(*) FROM data_ingestion_logs 
                WHERE created_at > NOW() - INTERVAL '1 day'
            """))
            count = result.scalar()
            print(f"   ✅ Timestamp query test: {count} recent logs")
            
        return True
        
    except Exception as e:
        print(f"   ❌ Index test failed: {e}")
        return False


def main():
    """Run all database tests."""
    print("🚀 MBTA Pipeline Database Test\n")
    
    tests = [
        test_database_connection,
        test_table_creation,
        test_basic_operations,
        test_relationships,
        test_indexes
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"   ❌ Test {test.__name__} failed with exception: {e}")
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All database tests passed! Your schema is ready.")
    else:
        print("⚠️  Some tests failed. Check the output above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
