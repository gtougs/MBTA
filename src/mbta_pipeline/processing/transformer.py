"""Data transformer for converting raw MBTA data to standardized models."""

from typing import Any, Dict, List, Optional, Union
from datetime import datetime
import logging

from .base import BaseProcessor
from ..models.transit import (
    Stop, Route, Trip, Prediction, 
    VehiclePosition, TripUpdate, Alert
)

logger = logging.getLogger(__name__)


class DataTransformer(BaseProcessor):
    """Transforms raw ingested data into standardized models."""
    
    def __init__(self):
        """Initialize the data transformer."""
        super().__init__("DataTransformer")
    
    def process(self, data: Any) -> Optional[Union[Stop, Route, Trip, Prediction, VehiclePosition, TripUpdate, Alert]]:
        """Transform raw data into a standardized model."""
        if isinstance(data, dict):
            return self._transform_dict(data)
        elif hasattr(data, 'SerializeToString'):  # Protobuf object
            return self._transform_protobuf(data)
        else:
            logger.warning(f"Unknown data type for transformation: {type(data)}")
            return None
    
    def _transform_dict(self, data: Dict[str, Any]) -> Optional[Union[Stop, Route, Trip, Prediction, VehiclePosition, TripUpdate, Alert]]:
        """Transform dictionary data."""
        # Try to determine the type based on content
        if 'stop_id' in data and 'stop_name' in data:
            return self._transform_stop(data)
        elif 'route_id' in data and 'route_name' in data:
            return self._transform_route(data)
        elif 'trip_id' in data and 'route_id' in data:
            return self._transform_trip(data)
        elif 'prediction_id' in data:
            return self._transform_prediction(data)
        elif 'vehicle_id' in data and 'latitude' in data and 'longitude' in data:
            return self._transform_vehicle_position(data)
        elif 'trip_id' in data and 'stop_time_updates' in data:
            return self._transform_trip_update(data)
        elif 'alert_id' in data or 'alert_header_text' in data:
            return self._transform_alert(data)
        else:
            logger.warning(f"Could not determine data type for: {list(data.keys())}")
            return None
    
    def _transform_protobuf(self, data: Any) -> Optional[Union[Stop, Route, Trip, Prediction, VehiclePosition, TripUpdate, Alert]]:
        """Transform protobuf data."""
        try:
            # Convert protobuf to dict first
            if hasattr(data, 'DESCRIPTOR'):
                # This is a protobuf message
                return self._transform_dict(self._protobuf_to_dict(data))
            else:
                logger.warning(f"Unknown protobuf type: {type(data)}")
                return None
        except Exception as e:
            logger.error(f"Error transforming protobuf data: {e}")
            return None
    
    def _protobuf_to_dict(self, message) -> Dict[str, Any]:
        """Convert protobuf message to dictionary."""
        result = {}
        for field in message.DESCRIPTOR.fields:
            value = getattr(message, field.name)
            if field.type == field.TYPE_MESSAGE:
                if field.label == field.LABEL_REPEATED:
                    result[field.name] = [self._protobuf_to_dict(item) for item in value]
                else:
                    result[field.name] = self._protobuf_to_dict(value) if value else None
            elif field.type == field.TYPE_ENUM:
                result[field.name] = field.enum_type.values_by_number[value].name if value else None
            else:
                result[field.name] = value
        return result
    
    def _transform_stop(self, data: Dict[str, Any]) -> Stop:
        """Transform stop data."""
        return Stop(
            stop_id=data['stop_id'],
            stop_name=data['stop_name'],
            stop_lat=data.get('stop_lat'),
            stop_lon=data.get('stop_lon'),
            wheelchair_boarding=data.get('wheelchair_boarding'),
            platform_code=data.get('platform_code')
        )
    
    def _transform_route(self, data: Dict[str, Any]) -> Route:
        """Transform route data."""
        return Route(
            route_id=data['route_id'],
            route_name=data['route_name'],
            route_type=data['route_type'],
            route_color=data.get('route_color'),
            route_text_color=data.get('route_text_color')
        )
    
    def _transform_trip(self, data: Dict[str, Any]) -> Trip:
        """Transform trip data."""
        return Trip(
            trip_id=data['trip_id'],
            route_id=data['route_id'],
            service_id=data.get('service_id'),
            trip_headsign=data.get('trip_headsign'),
            trip_short_name=data.get('trip_short_name'),
            direction_id=data.get('direction_id'),
            block_id=data.get('block_id'),
            shape_id=data.get('shape_id'),
            wheelchair_accessible=data.get('wheelchair_accessible'),
            bikes_allowed=data.get('bikes_allowed')
        )
    
    def _transform_prediction(self, data: Dict[str, Any]) -> Prediction:
        """Transform prediction data."""
        return Prediction(
            prediction_id=data['prediction_id'],
            trip_id=data['trip_id'],
            stop_id=data['stop_id'],
            route_id=data['route_id'],
            arrival_time=self._parse_datetime(data.get('arrival_time')),
            departure_time=self._parse_datetime(data.get('departure_time')),
            schedule_relationship=data.get('schedule_relationship'),
            vehicle_id=data.get('vehicle_id'),
            vehicle_label=data.get('vehicle_label'),
            status=data.get('status'),
            delay=data.get('delay')
        )
    
    def _transform_vehicle_position(self, data: Dict[str, Any]) -> VehiclePosition:
        """Transform vehicle position data."""
        return VehiclePosition(
            vehicle_id=data['vehicle_id'],
            trip_id=data.get('trip_id'),
            route_id=data.get('route_id'),
            latitude=data['latitude'],
            longitude=data['longitude'],
            bearing=data.get('bearing'),
            speed=data.get('speed'),
            current_status=data.get('current_status'),
            timestamp=self._parse_datetime(data['timestamp']),
            congestion_level=data.get('congestion_level'),
            occupancy_status=data.get('occupancy_status')
        )
    
    def _transform_trip_update(self, data: Dict[str, Any]) -> TripUpdate:
        """Transform trip update data."""
        return TripUpdate(
            trip_id=data['trip_id'],
            vehicle_id=data.get('vehicle_id'),
            route_id=data.get('route_id'),
            timestamp=self._parse_datetime(data['timestamp']),
            delay=data.get('delay'),
            stop_time_updates=data.get('stop_time_updates', [])
        )
    
    def _transform_alert(self, data: Dict[str, Any]) -> Alert:
        """Transform alert data."""
        return Alert(
            alert_id=data.get('alert_id', data.get('id', 'unknown')),
            alert_header_text=data.get('alert_header_text', data.get('header_text')),
            alert_description_text=data.get('alert_description_text', data.get('description_text')),
            alert_url=data.get('alert_url', data.get('url')),
            effective_start_date=self._parse_datetime(data.get('effective_start_date')),
            effective_end_date=self._parse_datetime(data.get('effective_end_date')),
            affected_routes=data.get('affected_routes', []),
            affected_stops=data.get('affected_stops', []),
            affected_trips=data.get('affected_trips', []),
            alert_severity_level=data.get('alert_severity_level', data.get('severity_level')),
            cause=data.get('cause'),
            effect=data.get('effect')
        )
    
    def _parse_datetime(self, value: Any) -> Optional[datetime]:
        """Parse datetime from various formats."""
        if value is None:
            return None
        
        if isinstance(value, datetime):
            return value
        
        if isinstance(value, str):
            try:
                # Try ISO format first
                return datetime.fromisoformat(value.replace('Z', '+00:00'))
            except ValueError:
                try:
                    # Try timestamp
                    return datetime.fromtimestamp(int(value))
                except (ValueError, TypeError):
                    logger.warning(f"Could not parse datetime: {value}")
                    return None
        
        if isinstance(value, (int, float)):
            try:
                return datetime.fromtimestamp(value)
            except (ValueError, OSError):
                logger.warning(f"Could not parse timestamp: {value}")
                return None
        
        return None
