"""Transit data models for MBTA API responses."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import Field, validator
from .base import BaseModel


class Stop(BaseModel):
    """MBTA stop information."""
    
    stop_id: str = Field(..., description="Unique stop identifier")
    stop_name: str = Field(..., description="Human-readable stop name")
    stop_lat: Optional[float] = Field(None, description="Stop latitude")
    stop_lon: Optional[float] = Field(None, description="Stop longitude")
    wheelchair_boarding: Optional[int] = Field(None, description="Wheelchair accessibility")
    platform_code: Optional[str] = Field(None, description="Platform identifier")
    
    source: str = Field("mbta_v3_api", description="Data source identifier")
    
    class Config:
        schema_extra = {
            "example": {
                "stop_id": "place-pktrm",
                "stop_name": "Park Street",
                "stop_lat": 42.3564,
                "stop_lon": -71.0624,
                "wheelchair_boarding": 1,
                "platform_code": "1"
            }
        }


class Route(BaseModel):
    """MBTA route information."""
    
    route_id: str = Field(..., description="Unique route identifier")
    route_name: str = Field(..., description="Human-readable route name")
    route_type: int = Field(..., description="Route type (0=tram, 1=subway, 2=rail, 3=bus)")
    route_color: Optional[str] = Field(None, description="Route color hex code")
    route_text_color: Optional[str] = Field(None, description="Route text color hex code")
    
    source: str = Field("mbta_v3_api", description="Data source identifier")
    
    class Config:
        schema_extra = {
            "example": {
                "route_id": "Red",
                "route_name": "Red Line",
                "route_type": 1,
                "route_color": "DA291C",
                "route_text_color": "FFFFFF"
            }
        }


class Trip(BaseModel):
    """MBTA trip information."""
    
    trip_id: str = Field(..., description="Unique trip identifier")
    route_id: str = Field(..., description="Associated route ID")
    service_id: Optional[str] = Field(None, description="Service pattern identifier")
    trip_headsign: Optional[str] = Field(None, description="Trip destination")
    trip_short_name: Optional[str] = Field(None, description="Short trip name")
    direction_id: Optional[int] = Field(None, description="Direction (0=outbound, 1=inbound)")
    block_id: Optional[str] = Field(None, description="Block identifier")
    shape_id: Optional[str] = Field(None, description="Shape identifier")
    wheelchair_accessible: Optional[int] = Field(None, description="Wheelchair accessibility")
    bikes_allowed: Optional[int] = Field(None, description="Bike allowance")
    
    source: str = Field("mbta_v3_api", description="Data source identifier")
    
    class Config:
        schema_extra = {
            "example": {
                "trip_id": "trip_123",
                "route_id": "Red",
                "service_id": "service_weekday",
                "trip_headsign": "Alewife",
                "direction_id": 0,
                "wheelchair_accessible": 1,
                "bikes_allowed": 1
            }
        }


class Prediction(BaseModel):
    """MBTA prediction data from V3 API."""
    
    prediction_id: str = Field(..., description="Unique prediction identifier")
    trip_id: str = Field(..., description="Associated trip ID")
    stop_id: str = Field(..., description="Associated stop ID")
    route_id: str = Field(..., description="Associated route ID")
    
    # Timing information
    arrival_time: Optional[datetime] = Field(None, description="Predicted arrival time")
    departure_time: Optional[datetime] = Field(None, description="Predicted departure time")
    schedule_relationship: Optional[str] = Field(None, description="Relationship to schedule")
    
    # Vehicle information
    vehicle_id: Optional[str] = Field(None, description="Associated vehicle ID")
    vehicle_label: Optional[str] = Field(None, description="Human-readable vehicle label")
    
    # Status information
    status: Optional[str] = Field(None, description="Prediction status")
    delay: Optional[int] = Field(None, description="Delay in seconds")
    
    # Related entities
    stop: Optional[Stop] = Field(None, description="Stop information")
    trip: Optional[Trip] = Field(None, description="Trip information")
    route: Optional[Route] = Field(None, description="Route information")
    
    source: str = Field("mbta_v3_api", description="Data source identifier")
    
    @validator('delay')
    def validate_delay(cls, v):
        """Validate delay is reasonable."""
        if v is not None and abs(v) > 3600:  # More than 1 hour
            raise ValueError("Delay seems unreasonable")
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "prediction_id": "pred_123",
                "trip_id": "trip_123",
                "stop_id": "place-pktrm",
                "route_id": "Red",
                "arrival_time": "2024-01-15T10:30:00Z",
                "departure_time": "2024-01-15T10:32:00Z",
                "vehicle_id": "vehicle_456",
                "delay": 120
            }
        }


class VehiclePosition(BaseModel):
    """MBTA vehicle position data from GTFS-RT."""
    
    vehicle_id: str = Field(..., description="Unique vehicle identifier")
    trip_id: Optional[str] = Field(None, description="Associated trip ID")
    route_id: Optional[str] = Field(None, description="Associated route ID")
    
    # Position information
    latitude: float = Field(..., description="Vehicle latitude")
    longitude: float = Field(..., description="Vehicle longitude")
    bearing: Optional[float] = Field(None, description="Vehicle bearing in degrees")
    speed: Optional[float] = Field(None, description="Vehicle speed in m/s")
    
    # Status information
    current_status: Optional[str] = Field(None, description="Current vehicle status")
    timestamp: datetime = Field(..., description="Position timestamp")
    congestion_level: Optional[str] = Field(None, description="Traffic congestion level")
    occupancy_status: Optional[str] = Field(None, description="Passenger occupancy status")
    
    source: str = Field("mbta_gtfs_rt", description="Data source identifier")
    
    @validator('latitude')
    def validate_latitude(cls, v):
        """Validate latitude is within reasonable bounds."""
        if not -90 <= v <= 90:
            raise ValueError("Latitude must be between -90 and 90")
        return v
    
    @validator('longitude')
    def validate_longitude(cls, v):
        """Validate longitude is within reasonable bounds."""
        if not -180 <= v <= 180:
            raise ValueError("Longitude must be between -180 and 180")
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "vehicle_id": "vehicle_456",
                "trip_id": "trip_123",
                "route_id": "Red",
                "latitude": 42.3564,
                "longitude": -71.0624,
                "bearing": 45.0,
                "speed": 15.5,
                "current_status": "IN_TRANSIT_TO",
                "timestamp": "2024-01-15T10:30:00Z"
            }
        }


class TripUpdate(BaseModel):
    """MBTA trip update data from GTFS-RT."""
    
    trip_id: str = Field(..., description="Unique trip identifier")
    vehicle_id: Optional[str] = Field(None, description="Associated vehicle ID")
    route_id: Optional[str] = Field(None, description="Associated route ID")
    
    # Update information
    timestamp: datetime = Field(..., description="Update timestamp")
    delay: Optional[int] = Field(None, description="Delay in seconds")
    
    # Stop updates
    stop_time_updates: List[Dict[str, Any]] = Field(default_factory=list, description="Stop time updates")
    
    source: str = Field("mbta_gtfs_rt", description="Data source identifier")
    
    class Config:
        schema_extra = {
            "example": {
                "trip_id": "trip_123",
                "vehicle_id": "vehicle_456",
                "route_id": "Red",
                "timestamp": "2024-01-15T10:30:00Z",
                "delay": 120,
                "stop_time_updates": [
                    {
                        "stop_id": "place-pktrm",
                        "arrival": {"delay": 120},
                        "departure": {"delay": 120}
                    }
                ]
            }
        }


class Alert(BaseModel):
    """MBTA service alert data from GTFS-RT."""
    
    alert_id: str = Field(..., description="Unique alert identifier")
    alert_header_text: Optional[str] = Field(None, description="Alert header text")
    alert_description_text: Optional[str] = Field(None, description="Alert description text")
    alert_url: Optional[str] = Field(None, description="Alert URL for more information")
    
    # Timing information
    effective_start_date: Optional[datetime] = Field(None, description="Alert start date")
    effective_end_date: Optional[datetime] = Field(None, description="Alert end date")
    
    # Affected entities
    affected_routes: List[str] = Field(default_factory=list, description="Affected route IDs")
    affected_stops: List[str] = Field(default_factory=list, description="Affected stop IDs")
    affected_trips: List[str] = Field(default_factory=list, description="Affected trip IDs")
    
    # Severity and cause
    alert_severity_level: Optional[str] = Field(None, description="Alert severity level")
    cause: Optional[str] = Field(None, description="Alert cause")
    effect: Optional[str] = Field(None, description="Alert effect")
    
    source: str = Field("mbta_gtfs_rt", description="Data source identifier")
    
    class Config:
        schema_extra = {
            "example": {
                "alert_id": "alert_789",
                "alert_header_text": "Red Line Delays",
                "alert_description_text": "Red Line service experiencing delays due to signal problems",
                "effective_start_date": "2024-01-15T10:00:00Z",
                "effective_end_date": "2024-01-15T18:00:00Z",
                "affected_routes": ["Red"],
                "alert_severity_level": "WARNING"
            }
        }
