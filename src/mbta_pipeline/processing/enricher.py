"""Data enricher for adding context and metadata to MBTA transit data."""

from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timezone
import logging

from .base import BaseProcessor
from ..models.transit import (
    Stop, Route, Trip, Prediction, 
    VehiclePosition, TripUpdate, Alert
)

logger = logging.getLogger(__name__)


class DataEnricher(BaseProcessor):
    """Enriches transit data with additional context and metadata."""
    
    def __init__(self):
        """Initialize the data enricher."""
        super().__init__("DataEnricher")
        self._route_cache = {}
        self._stop_cache = {}
        self._trip_cache = {}
    
    def process(self, data: Any) -> Any:
        """Enrich the input data with additional context."""
        if isinstance(data, Stop):
            return self._enrich_stop(data)
        elif isinstance(data, Route):
            return self._enrich_route(data)
        elif isinstance(data, Trip):
            return self._enrich_trip(data)
        elif isinstance(data, Prediction):
            return self._enrich_prediction(data)
        elif isinstance(data, VehiclePosition):
            return self._enrich_vehicle_position(data)
        elif isinstance(data, TripUpdate):
            return self._enrich_trip_update(data)
        elif isinstance(data, Alert):
            return self._enrich_alert(data)
        else:
            logger.warning(f"Unknown data type for enrichment: {type(data)}")
            return data
    
    def _enrich_stop(self, stop: Stop) -> Stop:
        """Enrich stop data with additional context."""
        # Add geographic context
        if stop.stop_lat and stop.stop_lon:
            # Add timezone (MBTA operates in Eastern Time)
            stop.metadata = {
                "timezone": "America/New_York",
                "geographic_region": self._get_geographic_region(stop.stop_lat, stop.stop_lon),
                "accessibility_features": self._get_accessibility_features(stop.wheelchair_boarding),
                "enriched_at": datetime.now(timezone.utc)
            }
        
        # Cache the stop for future reference
        self._stop_cache[stop.stop_id] = stop
        return stop
    
    def _enrich_route(self, route: Route) -> Route:
        """Enrich route data with additional context."""
        # Add route category and service information
        route.metadata = {
            "route_category": self._get_route_category(route.route_type),
            "service_area": self._get_service_area(route.route_id),
            "typical_frequency": self._get_typical_frequency(route.route_id),
            "enriched_at": datetime.now(timezone.utc)
        }
        
        # Cache the route for future reference
        self._route_cache[route.route_id] = route
        return route
    
    def _enrich_trip(self, trip: Trip) -> Trip:
        """Enrich trip data with additional context."""
        # Add trip context
        trip.metadata = {
            "direction_name": "Outbound" if trip.direction_id == 0 else "Inbound",
            "route_info": self._route_cache.get(trip.route_id),
            "enriched_at": datetime.now(timezone.utc)
        }
        
        # Cache the trip for future reference
        self._trip_cache[trip.trip_id] = trip
        return trip
    
    def _enrich_prediction(self, prediction: Prediction) -> Prediction:
        """Enrich prediction data with additional context."""
        # Add prediction context
        prediction.metadata = {
            "prediction_accuracy": self._calculate_prediction_accuracy(prediction),
            "service_status": self._get_service_status(prediction.delay),
            "enriched_at": datetime.now(timezone.utc)
        }
        
        # Link related entities if available
        if prediction.trip_id in self._trip_cache:
            prediction.trip = self._trip_cache[prediction.trip_id]
        if prediction.route_id in self._route_cache:
            prediction.route = self._route_cache[prediction.route_id]
        if prediction.stop_id in self._stop_cache:
            prediction.stop = self._stop_cache[prediction.stop_id]
        
        return prediction
    
    def _enrich_vehicle_position(self, position: VehiclePosition) -> VehiclePosition:
        """Enrich vehicle position data with additional context."""
        # Add position context
        position.metadata = {
            "location_accuracy": self._assess_location_accuracy(position),
            "speed_category": self._categorize_speed(position.speed),
            "service_area": self._get_service_area(position.route_id) if position.route_id else None,
            "enriched_at": datetime.now(timezone.utc)
        }
        
        # Link related entities if available
        if position.trip_id in self._trip_cache:
            position.trip = self._trip_cache[position.trip_id]
        if position.route_id in self._route_cache:
            position.route = self._route_cache[position.route_id]
        
        return position
    
    def _enrich_trip_update(self, update: TripUpdate) -> TripUpdate:
        """Enrich trip update data with additional context."""
        # Add update context
        update.metadata = {
            "update_significance": self._assess_update_significance(update),
            "affected_stops_count": len(update.stop_time_updates),
            "enriched_at": datetime.now(timezone.utc)
        }
        
        # Link related entities if available
        if update.trip_id in self._trip_cache:
            update.trip = self._trip_cache[update.trip_id]
        if update.route_id in self._route_cache:
            update.route = self._route_cache[update.route_id]
        
        return update
    
    def _enrich_alert(self, alert: Alert) -> Alert:
        """Enrich alert data with additional context."""
        # Add alert context
        alert.metadata = {
            "alert_priority": self._calculate_alert_priority(alert),
            "affected_services": self._get_affected_services(alert),
            "enriched_at": datetime.now(timezone.utc)
        }
        
        return alert
    
    def _get_geographic_region(self, lat: float, lon: float) -> str:
        """Determine geographic region based on coordinates."""
        # Simple geographic regions for MBTA service area
        if lat > 42.4:  # North of Boston
            return "North Shore"
        elif lat < 42.3:  # South of Boston
            return "South Shore"
        elif lon > -71.0:  # East of Boston
            return "East Boston"
        elif lon < -71.1:  # West of Boston
            return "West Boston"
        else:
            return "Central Boston"
    
    def _get_accessibility_features(self, wheelchair_boarding: Optional[int]) -> List[str]:
        """Get accessibility features based on wheelchair boarding code."""
        if wheelchair_boarding is None:
            return ["unknown"]
        
        features = []
        if wheelchair_boarding == 1:
            features.append("wheelchair_accessible")
        elif wheelchair_boarding == 2:
            features.append("wheelchair_inaccessible")
        
        return features
    
    def _get_route_category(self, route_type: int) -> str:
        """Get route category based on route type."""
        categories = {
            0: "Light Rail",
            1: "Subway",
            2: "Commuter Rail",
            3: "Bus",
            4: "Ferry"
        }
        return categories.get(route_type, "Unknown")
    
    def _get_service_area(self, route_id: str) -> str:
        """Get service area based on route ID."""
        if route_id.startswith("CR-"):
            return "Commuter Rail"
        elif route_id.startswith("Green-"):
            return "Green Line"
        elif route_id in ["Red", "Blue", "Orange"]:
            return "Subway"
        elif route_id.startswith("SL"):
            return "Silver Line"
        else:
            return "Bus"
    
    def _get_typical_frequency(self, route_id: str) -> str:
        """Get typical service frequency for a route."""
        if route_id.startswith("CR-"):
            return "Peak hours only"
        elif route_id in ["Red", "Blue", "Orange"]:
            return "Every 3-10 minutes"
        elif route_id.startswith("Green-"):
            return "Every 5-15 minutes"
        else:
            return "Every 10-30 minutes"
    
    def _calculate_prediction_accuracy(self, prediction: Prediction) -> str:
        """Calculate prediction accuracy based on available data."""
        if prediction.delay is not None:
            if abs(prediction.delay) < 60:
                return "high"
            elif abs(prediction.delay) < 300:
                return "medium"
            else:
                return "low"
        return "unknown"
    
    def _get_service_status(self, delay: Optional[int]) -> str:
        """Get service status based on delay."""
        if delay is None:
            return "on_time"
        elif delay <= 0:
            return "on_time"
        elif delay <= 300:  # 5 minutes
            return "minor_delay"
        elif delay <= 900:  # 15 minutes
            return "moderate_delay"
        else:
            return "major_delay"
    
    def _assess_location_accuracy(self, position: VehiclePosition) -> str:
        """Assess the accuracy of vehicle location data."""
        # This would typically use GPS accuracy data if available
        return "good"  # Placeholder
    
    def _categorize_speed(self, speed: Optional[float]) -> str:
        """Categorize vehicle speed."""
        if speed is None:
            return "unknown"
        elif speed < 5:
            return "stopped"
        elif speed < 15:
            return "slow"
        elif speed < 30:
            return "normal"
        else:
            return "fast"
    
    def _assess_update_significance(self, update: TripUpdate) -> str:
        """Assess the significance of a trip update."""
        if not update.stop_time_updates:
            return "minor"
        
        # Count significant delays
        significant_delays = 0
        for stop_update in update.stop_time_updates:
            if isinstance(stop_update, dict):
                delay = stop_update.get('delay', 0)
                if abs(delay) > 300:  # 5 minutes
                    significant_delays += 1
        
        if significant_delays == 0:
            return "minor"
        elif significant_delays <= 2:
            return "moderate"
        else:
            return "major"
    
    def _calculate_alert_priority(self, alert: Alert) -> str:
        """Calculate alert priority based on severity and affected entities."""
        if alert.alert_severity_level == "SEVERE":
            return "high"
        elif alert.alert_severity_level == "WARNING":
            return "medium"
        else:
            return "low"
    
    def _get_affected_services(self, alert: Alert) -> List[str]:
        """Get list of affected services from alert."""
        services = set()
        
        if alert.affected_routes:
            for route_id in alert.affected_routes:
                services.add(self._get_service_area(route_id))
        
        if alert.affected_stops:
            services.add("Multiple stops affected")
        
        return list(services) if services else ["Unknown"]
