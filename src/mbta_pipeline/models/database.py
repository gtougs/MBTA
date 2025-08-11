"""Database models for MBTA transit data using SQLAlchemy."""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Boolean, 
    Text, ForeignKey, Index, UniqueConstraint, JSON
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Mapped
from sqlalchemy.dialects.postgresql import UUID
import uuid

Base = declarative_base()


class Route(Base):
    """MBTA route information."""
    __tablename__ = 'routes'
    
    id = Column(String(50), primary_key=True)
    route_name = Column(String(100), nullable=False)
    route_type = Column(Integer, nullable=False)
    route_color = Column(String(7))  # Hex color code
    route_text_color = Column(String(7))  # Hex color code
    route_sort_order = Column(Integer)
    route_long_name = Column(String(200))
    route_desc = Column(Text)
    
    # Relationships
    trips: Mapped[List["Trip"]] = relationship("Trip", back_populates="route")
    predictions: Mapped[List["Prediction"]] = relationship("Prediction", back_populates="route")
    
    # Indexes
    __table_args__ = (
        Index('idx_routes_type', 'route_type'),
        Index('idx_routes_name', 'route_name'),
    )


class Stop(Base):
    """MBTA stop information."""
    __tablename__ = 'stops'
    
    id = Column(String(50), primary_key=True)
    stop_name = Column(String(200), nullable=False)
    stop_lat = Column(Float)
    stop_lon = Column(Float)
    stop_code = Column(String(50))
    stop_desc = Column(Text)
    zone_id = Column(String(50))
    stop_url = Column(String(500))
    location_type = Column(Integer, default=0)
    parent_station = Column(String(50), ForeignKey('stops.id'))
    wheelchair_boarding = Column(Integer, default=0)
    
    # Relationships
    predictions: Mapped[List["Prediction"]] = relationship("Prediction", back_populates="stop")
    
    # Indexes
    __table_args__ = (
        Index('idx_stops_name', 'stop_name'),
        Index('idx_stops_location', 'stop_lat', 'stop_lon'),
        Index('idx_stops_parent', 'parent_station'),
    )


class Trip(Base):
    """MBTA trip information."""
    __tablename__ = 'trips'
    
    id = Column(String(50), primary_key=True)
    route_id = Column(String(50), ForeignKey('routes.id'), nullable=False)
    service_id = Column(String(50), nullable=False)
    trip_headsign = Column(String(100))
    trip_short_name = Column(String(50))
    direction_id = Column(Integer)
    block_id = Column(String(50))
    shape_id = Column(String(50))
    wheelchair_accessible = Column(Integer, default=0)
    bikes_allowed = Column(Integer, default=0)
    
    # Relationships
    route: Mapped["Route"] = relationship("Route", back_populates="trips")
    predictions: Mapped[List["Prediction"]] = relationship("Prediction", back_populates="trip")
    trip_updates: Mapped[List["TripUpdate"]] = relationship("TripUpdate", back_populates="trip")
    
    # Indexes
    __table_args__ = (
        Index('idx_trips_route', 'route_id'),
        Index('idx_trips_service', 'service_id'),
        Index('idx_trips_direction', 'direction_id'),
    )


class Vehicle(Base):
    """MBTA vehicle information."""
    __tablename__ = 'vehicles'
    
    id = Column(String(50), primary_key=True)
    vehicle_id = Column(String(50), unique=True, nullable=False)
    vehicle_label = Column(String(100))
    vehicle_license_plate = Column(String(20))
    vehicle_type = Column(Integer)
    vehicle_capacity = Column(Integer)
    
    # Relationships
    vehicle_positions: Mapped[List["VehiclePosition"]] = relationship("VehiclePosition", back_populates="vehicle")
    
    # Indexes
    __table_args__ = (
        Index('idx_vehicles_type', 'vehicle_type'),
        Index('idx_vehicles_label', 'vehicle_label'),
    )


class VehiclePosition(Base):
    """Real-time vehicle position data."""
    __tablename__ = 'vehicle_positions'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vehicle_id = Column(String(50), ForeignKey('vehicles.vehicle_id'), nullable=False)
    trip_id = Column(String(50), ForeignKey('trips.id'))
    route_id = Column(String(50), ForeignKey('routes.id'))
    direction_id = Column(Integer)
    stop_id = Column(String(50), ForeignKey('stops.id'))
    
    # Position data
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    bearing = Column(Float)
    speed = Column(Float)
    congestion_level = Column(Integer)
    occupancy_status = Column(Integer)
    
    # Timestamps
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    vehicle: Mapped["Vehicle"] = relationship("Vehicle", back_populates="vehicle_positions")
    trip: Mapped[Optional["Trip"]] = relationship("Trip")
    route: Mapped[Optional["Route"]] = relationship("Route")
    stop: Mapped[Optional["Stop"]] = relationship("Stop")
    
    # Indexes
    __table_args__ = (
        Index('idx_vehicle_positions_vehicle', 'vehicle_id'),
        Index('idx_vehicle_positions_trip', 'trip_id'),
        Index('idx_vehicle_positions_timestamp', 'timestamp'),
        Index('idx_vehicle_positions_location', 'latitude', 'longitude'),
    )


class Prediction(Base):
    """Real-time arrival predictions."""
    __tablename__ = 'predictions'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trip_id = Column(String(50), ForeignKey('trips.id'), nullable=False)
    route_id = Column(String(50), ForeignKey('routes.id'), nullable=False)
    stop_id = Column(String(50), ForeignKey('stops.id'), nullable=False)
    vehicle_id = Column(String(50), ForeignKey('vehicles.vehicle_id'))
    
    # Prediction data
    arrival_time = Column(DateTime)
    departure_time = Column(DateTime)
    schedule_relationship = Column(Integer, default=0)
    
    # Status
    status = Column(String(50))
    delay = Column(Integer)  # Delay in seconds
    
    # Timestamps
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    trip: Mapped["Trip"] = relationship("Trip", back_populates="predictions")
    route: Mapped["Route"] = relationship("Route", back_populates="predictions")
    stop: Mapped["Stop"] = relationship("Stop", back_populates="predictions")
    vehicle: Mapped[Optional["Vehicle"]] = relationship("Vehicle")
    
    # Indexes
    __table_args__ = (
        Index('idx_predictions_trip', 'trip_id'),
        Index('idx_predictions_stop', 'stop_id'),
        Index('idx_predictions_timestamp', 'timestamp'),
        Index('idx_predictions_arrival', 'arrival_time'),
        UniqueConstraint('trip_id', 'stop_id', 'arrival_time', name='uq_prediction_trip_stop_time'),
    )


class TripUpdate(Base):
    """Real-time trip updates and delays."""
    __tablename__ = 'trip_updates'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trip_id = Column(String(50), ForeignKey('trips.id'), nullable=False)
    route_id = Column(String(50), ForeignKey('routes.id'))
    
    # Update data
    delay = Column(Integer)  # Delay in seconds
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    
    # Timestamps
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    trip: Mapped["Trip"] = relationship("Trip", back_populates="trip_updates")
    route: Mapped[Optional["Route"]] = relationship("Route")
    
    # Indexes
    __table_args__ = (
        Index('idx_trip_updates_trip', 'trip_id'),
        Index('idx_trip_updates_timestamp', 'timestamp'),
        Index('idx_trip_updates_delay', 'delay'),
    )


class Alert(Base):
    """Service alerts and notifications."""
    __tablename__ = 'alerts'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    alert_id = Column(String(50), unique=True, nullable=False)
    
    # Alert data
    alert_header_text = Column(Text)
    alert_description_text = Column(Text)
    alert_url = Column(String(500))
    alert_effect = Column(String(100))
    alert_severity_level = Column(String(50))
    
    # Affected entities
    affected_route_ids = Column(JSON)  # Array of route IDs
    affected_stop_ids = Column(JSON)   # Array of stop IDs
    affected_trip_ids = Column(JSON)   # Array of trip IDs
    
    # Timestamps
    active_period_start = Column(DateTime)
    active_period_end = Column(DateTime)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        Index('idx_alerts_timestamp', 'timestamp'),
        Index('idx_alerts_effect', 'alert_effect'),
        Index('idx_alerts_severity', 'alert_severity_level'),
    )


class DataIngestionLog(Base):
    """Log of data ingestion activities."""
    __tablename__ = 'data_ingestion_logs'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Ingestion metadata
    source_type = Column(String(50), nullable=False)  # 'v3_api', 'gtfs_rt', etc.
    endpoint = Column(String(200))
    status = Column(String(50), nullable=False)  # 'success', 'error', 'partial'
    
    # Data counts
    records_processed = Column(Integer, default=0)
    records_inserted = Column(Integer, default=0)
    records_updated = Column(Integer, default=0)
    records_failed = Column(Integer, default=0)
    
    # Error details
    error_message = Column(Text)
    error_details = Column(JSON)
    
    # Performance metrics
    processing_time_ms = Column(Integer)
    response_time_ms = Column(Integer)
    
    # Timestamps
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        Index('idx_ingestion_logs_source', 'source_type'),
        Index('idx_ingestion_logs_status', 'status'),
        Index('idx_ingestion_logs_timestamp', 'started_at'),
    )
