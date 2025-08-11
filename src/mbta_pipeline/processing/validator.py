"""Data validator for ensuring MBTA transit data quality and consistency."""

from typing import Any, Dict, List, Optional, Union, Tuple
from datetime import datetime, timedelta
import logging
from datetime import timezone

from .base import BaseProcessor
from ..models.transit import (
    Stop, Route, Trip, Prediction, 
    VehiclePosition, TripUpdate, Alert
)

logger = logging.getLogger(__name__)


class DataValidator(BaseProcessor):
    """Validates transit data for quality and consistency."""
    
    def __init__(self):
        """Initialize the data validator."""
        super().__init__("DataValidator")
        self.validation_rules = self._setup_validation_rules()
    
    def process(self, data: Any) -> Optional[Any]:
        """Validate the input data and return if valid, None if invalid."""
        try:
            if isinstance(data, Stop):
                return self._validate_stop(data)
            elif isinstance(data, Route):
                return self._validate_route(data)
            elif isinstance(data, Trip):
                return self._validate_trip(data)
            elif isinstance(data, Prediction):
                return self._validate_prediction(data)
            elif isinstance(data, VehiclePosition):
                return self._validate_vehicle_position(data)
            elif isinstance(data, TripUpdate):
                return self._validate_trip_update(data)
            elif isinstance(data, Alert):
                return self._validate_alert(data)
            else:
                logger.warning(f"Unknown data type for validation: {type(data)}")
                return None
        except Exception as e:
            logger.error(f"Validation error for {type(data).__name__}: {e}")
            return None
    
    def _setup_validation_rules(self) -> Dict[str, Dict]:
        """Setup validation rules for different data types."""
        return {
            "stop": {
                "required_fields": ["stop_id", "stop_name"],
                "coordinate_bounds": {
                    "lat_min": 42.0, "lat_max": 43.0,
                    "lon_min": -71.5, "lon_max": -70.5
                }
            },
            "route": {
                "required_fields": ["route_id", "route_name", "route_type"],
                "route_type_range": (0, 4)
            },
            "trip": {
                "required_fields": ["trip_id", "route_id"],
                "direction_id_range": (0, 1)
            },
            "prediction": {
                "required_fields": ["prediction_id", "trip_id", "stop_id", "route_id"],
                "delay_bounds": (-3600, 3600),  # ±1 hour
                "max_future_prediction": timedelta(hours=2)
            },
            "vehicle_position": {
                "required_fields": ["vehicle_id", "latitude", "longitude", "timestamp"],
                "coordinate_bounds": {
                    "lat_min": 42.0, "lat_max": 43.0,
                    "lon_min": -71.5, "lon_max": -70.5
                },
                "speed_bounds": (0, 50),  # m/s
                "max_age": timedelta(minutes=30)
            },
            "trip_update": {
                "required_fields": ["trip_id", "timestamp"],
                "max_age": timedelta(hours=1)
            },
            "alert": {
                "required_fields": ["alert_id"],
                "max_age": timedelta(days=7)
            }
        }
    
    def _validate_stop(self, stop: Stop) -> Optional[Stop]:
        """Validate stop data."""
        rules = self.validation_rules["stop"]
        
        # Check required fields
        if not self._check_required_fields(stop, rules["required_fields"]):
            return None
        
        # Validate coordinates if present
        if stop.stop_lat is not None and stop.stop_lon is not None:
            if not self._validate_coordinates(
                stop.stop_lat, stop.stop_lon, rules["coordinate_bounds"]
            ):
                logger.warning(f"Invalid coordinates for stop {stop.stop_id}")
                return None
        
        # Validate wheelchair boarding code
        if stop.wheelchair_boarding is not None:
            if stop.wheelchair_boarding not in [0, 1, 2]:
                logger.warning(f"Invalid wheelchair_boarding code for stop {stop.stop_id}")
                return None
        
        return stop
    
    def _validate_route(self, route: Route) -> Optional[Route]:
        """Validate route data."""
        rules = self.validation_rules["route"]
        
        # Check required fields
        if not self._check_required_fields(route, rules["required_fields"]):
            return None
        
        # Validate route type
        if not self._validate_range(
            route.route_type, rules["route_type_range"]
        ):
            logger.warning(f"Invalid route_type for route {route.route_id}")
            return None
        
        # Validate color codes if present
        if route.route_color and not self._validate_hex_color(route.route_color):
            logger.warning(f"Invalid route_color for route {route.route_id}")
            return None
        
        if route.route_text_color and not self._validate_hex_color(route.route_text_color):
            logger.warning(f"Invalid route_text_color for route {route.route_id}")
            return None
        
        return route
    
    def _validate_trip(self, trip: Trip) -> Optional[Trip]:
        """Validate trip data."""
        rules = self.validation_rules["trip"]
        
        # Check required fields
        if not self._check_required_fields(trip, rules["required_fields"]):
            return None
        
        # Validate direction_id if present
        if trip.direction_id is not None:
            if not self._validate_range(
                trip.direction_id, rules["direction_id_range"]
            ):
                logger.warning(f"Invalid direction_id for trip {trip.trip_id}")
                return None
        
        # Validate accessibility codes if present
        if trip.wheelchair_accessible is not None:
            if trip.wheelchair_accessible not in [0, 1, 2]:
                logger.warning(f"Invalid wheelchair_accessible code for trip {trip.trip_id}")
                return None
        
        if trip.bikes_allowed is not None:
            if trip.bikes_allowed not in [0, 1, 2]:
                logger.warning(f"Invalid bikes_allowed code for trip {trip.trip_id}")
                return None
        
        return trip
    
    def _validate_prediction(self, prediction: Prediction) -> Optional[Prediction]:
        """Validate prediction data."""
        rules = self.validation_rules["prediction"]
        
        # Check required fields
        if not self._check_required_fields(prediction, rules["required_fields"]):
            return None
        
        # Validate delay bounds
        if prediction.delay is not None:
            if not self._validate_range(
                prediction.delay, rules["delay_bounds"]
            ):
                logger.warning(f"Invalid delay value for prediction {prediction.prediction_id}")
                return None
        
        # Validate timing if present
        if prediction.arrival_time:
            if not self._validate_future_time(
                prediction.arrival_time, rules["max_future_prediction"]
            ):
                logger.warning(f"Invalid arrival_time for prediction {prediction.prediction_id}")
                return None
        
        if prediction.departure_time:
            if not self._validate_future_time(
                prediction.departure_time, rules["max_future_prediction"]
            ):
                logger.warning(f"Invalid departure_time for prediction {prediction.prediction_id}")
                return None
        
        return prediction
    
    def _validate_vehicle_position(self, position: VehiclePosition) -> Optional[VehiclePosition]:
        """Validate vehicle position data."""
        rules = self.validation_rules["vehicle_position"]
        
        # Check required fields
        if not self._check_required_fields(position, rules["required_fields"]):
            return None
        
        # Validate coordinates
        if not self._validate_coordinates(
            position.latitude, position.longitude, rules["coordinate_bounds"]
        ):
            logger.warning(f"Invalid coordinates for vehicle {position.vehicle_id}")
            return None
        
        # Validate speed if present
        if position.speed is not None:
            if not self._validate_range(
                position.speed, rules["speed_bounds"]
            ):
                logger.warning(f"Invalid speed for vehicle {position.vehicle_id}")
                return None
        
        # Validate timestamp age
        if not self._validate_timestamp_age(
            position.timestamp, rules["max_age"]
        ):
            logger.warning(f"Timestamp too old for vehicle {position.vehicle_id}")
            return None
        
        # Validate bearing if present
        if position.bearing is not None:
            if not self._validate_range(position.bearing, (0, 360)):
                logger.warning(f"Invalid bearing for vehicle {position.vehicle_id}")
                return None
        
        return position
    
    def _validate_trip_update(self, update: TripUpdate) -> Optional[TripUpdate]:
        """Validate trip update data."""
        rules = self.validation_rules["trip_update"]
        
        # Check required fields
        if not self._check_required_fields(update, rules["required_fields"]):
            return None
        
        # Validate timestamp age
        if not self._validate_timestamp_age(
            update.timestamp, rules["max_age"]
        ):
            logger.warning(f"Timestamp too old for trip update {update.trip_id}")
            return None
        
        # Validate delay if present
        if update.delay is not None:
            if not self._validate_range(update.delay, (-3600, 3600)):
                logger.warning(f"Invalid delay for trip update {update.trip_id}")
                return None
        
        return update
    
    def _validate_alert(self, alert: Alert) -> Optional[Alert]:
        """Validate alert data."""
        rules = self.validation_rules["alert"]
        
        # Check required fields
        if not self._check_required_fields(alert, rules["required_fields"]):
            return None
        
        # Validate dates if present
        if alert.effective_start_date and alert.effective_end_date:
            if alert.effective_start_date >= alert.effective_end_date:
                logger.warning(f"Invalid date range for alert {alert.alert_id}")
                return None
        
        # Validate severity level if present
        valid_severities = ["INFO", "WARNING", "SEVERE"]
        if alert.alert_severity_level and alert.alert_severity_level not in valid_severities:
            logger.warning(f"Invalid severity level for alert {alert.alert_id}")
            return None
        
        return alert
    
    def _check_required_fields(self, obj: Any, required_fields: List[str]) -> bool:
        """Check if all required fields are present and non-empty."""
        for field in required_fields:
            value = getattr(obj, field, None)
            if value is None or (isinstance(value, str) and not value.strip()):
                logger.warning(f"Missing required field: {field}")
                return False
        return True
    
    def _validate_coordinates(self, lat: float, lon: float, bounds: Dict) -> bool:
        """Validate coordinate bounds."""
        return (
            bounds["lat_min"] <= lat <= bounds["lat_max"] and
            bounds["lon_min"] <= lon <= bounds["lon_max"]
        )
    
    def _validate_range(self, value: Union[int, float], bounds: Tuple) -> bool:
        """Validate value is within range."""
        return bounds[0] <= value <= bounds[1]
    
    def _validate_hex_color(self, color: str) -> bool:
        """Validate hex color code format."""
        if not color:
            return False
        # Remove # if present
        color = color.lstrip('#')
        return len(color) == 6 and all(c in '0123456789ABCDEFabcdef' for c in color)
    
    def _validate_future_time(self, time: datetime, max_future: timedelta) -> bool:
        """Validate time is not too far in the future."""
        now = datetime.now(time.utc if time.tzinfo else time.replace(tzinfo=timezone.utc))
        return time > now and (time - now) <= max_future
    
    def _validate_timestamp_age(self, timestamp: datetime, max_age: timedelta) -> bool:
        """Validate timestamp is not too old."""
        now = datetime.now(timestamp.tzinfo if timestamp.tzinfo else timezone.utc)
        return (now - timestamp) <= max_age
    
    def get_validation_summary(self) -> Dict[str, Any]:
        """Get validation statistics summary."""
        return {
            "processor": self.name,
            "processed_count": self.processed_count,
            "error_count": self.error_count,
            "success_rate": (
                self.processed_count / (self.processed_count + self.error_count)
                if (self.processed_count + self.error_count) > 0 else 0
            ),
            "validation_rules": len(self.validation_rules)
        }
