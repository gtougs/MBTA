"""GTFS-RT protobuf ingestor for MBTA real-time data."""

import asyncio
import aiohttp
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
import io

from .base import BaseIngestor
from ..config.settings import settings
from ..models.transit import VehiclePosition, TripUpdate, Alert
from ..utils.logging import get_logger

# GTFS-RT imports
try:
    from google.transit import gtfs_realtime_pb2
    GTFS_RT_AVAILABLE = True
except ImportError:
    GTFS_RT_AVAILABLE = False
    print("Warning: GTFS-RT protobuf bindings not available. Install with: pip install gtfs-realtime-bindings")


class GTFSRTIngestor(BaseIngestor):
    """Ingestor for MBTA GTFS-RT protobuf feeds."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the GTFS-RT ingestor."""
        super().__init__("mbta_gtfs_rt", config)
        
        if not GTFS_RT_AVAILABLE:
            raise ImportError("GTFS-RT protobuf bindings required. Install with: pip install gtfs-realtime-bindings")
        
        # GTFS-RT endpoints
        self.base_url = settings.mbta_gtfs_rt_base_url
        self.endpoints = {
            "vehicle_positions": "/VehiclePositions.pb",
            "trip_updates": "/TripUpdates.pb",
            "alerts": "/Alerts.pb"
        }
        
        # Session for HTTP requests
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Feed metadata
        self.feed_timestamps = {}
        self.feed_sequence_numbers = {}
        
        self.logger = get_logger(f"{self.__class__.__name__}")
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            headers={
                "User-Agent": "MBTA-Data-Pipeline/1.0",
                "Accept": "application/x-protobuf"
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def initialize_session(self):
        """Initialize the HTTP session."""
        if not self.session:
            self.session = aiohttp.ClientSession(
                headers={
                    "User-Agent": "MBTA-Data-Pipeline/1.0",
                    "Accept": "application/x-protobuf"
                }
            )
    
    async def _fetch_protobuf_feed(self, endpoint: str) -> Optional[bytes]:
        """Fetch a protobuf feed from the MBTA GTFS-RT endpoint."""
        url = f"{self.base_url}{endpoint}"
        
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.read()
                    self.logger.debug(f"Successfully fetched {endpoint}: {len(data)} bytes")
                    return data
                else:
                    self.logger.warning(f"Failed to fetch {endpoint}: HTTP {response.status}")
                    return None
                    
        except Exception as e:
            self.logger.error(f"Error fetching {endpoint}: {str(e)}", exc_info=True)
            return None
    
    async def _parse_vehicle_positions(self, protobuf_data: bytes) -> List[Dict[str, Any]]:
        """Parse vehicle positions from GTFS-RT protobuf."""
        try:
            feed = gtfs_realtime_pb2.FeedMessage()
            feed.ParseFromString(protobuf_data)
            
            # Update feed metadata
            self.feed_timestamps["vehicle_positions"] = datetime.fromtimestamp(feed.header.timestamp)
            self.feed_sequence_numbers["vehicle_positions"] = feed.header.gtfs_realtime_version
            
            vehicles = []
            for entity in feed.entity:
                if entity.HasField("vehicle"):
                    vehicle_data = entity.vehicle
                    position = vehicle_data.position
                    
                    # Parse timestamp
                    timestamp = None
                    if vehicle_data.HasField("timestamp"):
                        timestamp = datetime.fromtimestamp(vehicle_data.timestamp)
                    
                    vehicle = {
                        "vehicle_id": entity.id,
                        "trip_id": vehicle_data.trip.trip_id if vehicle_data.HasField("trip") else None,
                        "route_id": vehicle_data.trip.route_id if vehicle_data.HasField("trip") else None,
                        "latitude": position.lat,
                        "longitude": position.lon,
                        "bearing": position.bearing if position.HasField("bearing") else None,
                        "speed": position.speed if position.HasField("speed") else None,
                        "current_status": vehicle_data.current_status if vehicle_data.HasField("current_status") else None,
                        "timestamp": timestamp,
                        "congestion_level": vehicle_data.congestion_level if vehicle_data.HasField("congestion_level") else None,
                        "occupancy_status": vehicle_data.occupancy_status if vehicle_data.HasField("occupancy_status") else None,
                        "source": "mbta_gtfs_rt",
                        "feed_timestamp": self.feed_timestamps["vehicle_positions"],
                        "raw_entity": entity
                    }
                    
                    vehicles.append(vehicle)
            
            self.logger.info(f"Parsed {len(vehicles)} vehicle positions from GTFS-RT")
            return vehicles
            
        except Exception as e:
            self.logger.error(f"Error parsing vehicle positions: {str(e)}", exc_info=True)
            return []
    
    async def _parse_trip_updates(self, protobuf_data: bytes) -> List[Dict[str, Any]]:
        """Parse trip updates from GTFS-RT protobuf."""
        try:
            feed = gtfs_realtime_pb2.FeedMessage()
            feed.ParseFromString(protobuf_data)
            
            # Update feed metadata
            self.feed_timestamps["trip_updates"] = datetime.fromtimestamp(feed.header.timestamp)
            self.feed_sequence_numbers["trip_updates"] = feed.header.gtfs_realtime_version
            
            trip_updates = []
            for entity in feed.entity:
                if entity.HasField("trip_update"):
                    trip_update_data = entity.trip_update
                    
                    # Parse timestamp
                    timestamp = None
                    if feed.header.HasField("timestamp"):
                        timestamp = datetime.fromtimestamp(feed.header.timestamp)
                    
                    # Extract stop time updates
                    stop_time_updates = []
                    for stop_update in trip_update_data.stop_time_update:
                        stop_update_dict = {
                            "stop_id": stop_update.stop_id,
                            "stop_sequence": stop_update.stop_sequence if stop_update.HasField("stop_sequence") else None
                        }
                        
                        if stop_update.HasField("arrival"):
                            stop_update_dict["arrival"] = {
                                "delay": stop_update.arrival.delay if stop_update.arrival.HasField("delay") else None,
                                "time": stop_update.arrival.time if stop_update.arrival.HasField("time") else None
                            }
                        
                        if stop_update.HasField("departure"):
                            stop_update_dict["departure"] = {
                                "delay": stop_update.departure.delay if stop_update.departure.HasField("delay") else None,
                                "time": stop_update.departure.time if stop_update.departure.HasField("time") else None
                            }
                        
                        stop_time_updates.append(stop_update_dict)
                    
                    trip_update = {
                        "trip_id": entity.id,
                        "vehicle_id": trip_update_data.vehicle.id if trip_update_data.HasField("vehicle") else None,
                        "route_id": trip_update_data.trip.route_id if trip_update_data.HasField("trip") else None,
                        "timestamp": timestamp,
                        "delay": None,  # Will be calculated from stop updates
                        "stop_time_updates": stop_time_updates,
                        "source": "mbta_gtfs_rt",
                        "feed_timestamp": self.feed_timestamps["trip_updates"],
                        "raw_entity": entity
                    }
                    
                    # Calculate overall delay (average of all stop delays)
                    delays = []
                    for stop_update in stop_time_updates:
                        if "arrival" in stop_update and stop_update["arrival"].get("delay"):
                            delays.append(stop_update["arrival"]["delay"])
                        if "departure" in stop_update and stop_update["departure"].get("delay"):
                            delays.append(stop_update["departure"]["delay"])
                    
                    if delays:
                        trip_update["delay"] = sum(delays) / len(delays)
                    
                    trip_updates.append(trip_update)
            
            self.logger.info(f"Parsed {len(trip_updates)} trip updates from GTFS-RT")
            return trip_updates
            
        except Exception as e:
            self.logger.error(f"Error parsing trip updates: {str(e)}", exc_info=True)
            return []
    
    async def _parse_alerts(self, protobuf_data: bytes) -> List[Dict[str, Any]]:
        """Parse service alerts from GTFS-RT protobuf."""
        try:
            feed = gtfs_realtime_pb2.FeedMessage()
            feed.ParseFromString(protobuf_data)
            
            # Update feed metadata
            self.feed_timestamps["alerts"] = datetime.fromtimestamp(feed.header.timestamp)
            self.feed_sequence_numbers["alerts"] = feed.header.gtfs_realtime_version
            
            alerts = []
            for entity in feed.entity:
                if entity.HasField("alert"):
                    alert_data = entity.alert
                    
                    # Parse effective dates
                    effective_start_date = None
                    effective_end_date = None
                    
                    if alert_data.HasField("active_period"):
                        for period in alert_data.active_period:
                            if period.HasField("start"):
                                effective_start_date = datetime.fromtimestamp(period.start)
                            if period.HasField("end"):
                                effective_end_date = datetime.fromtimestamp(period.end)
                    
                    # Extract affected entities
                    affected_routes = []
                    affected_stops = []
                    affected_trips = []
                    
                    for entity_ref in alert_data.informed_entity:
                        if entity_ref.HasField("route_id"):
                            affected_routes.append(entity_ref.route_id)
                        if entity_ref.HasField("stop_id"):
                            affected_stops.append(entity_ref.stop_id)
                        if entity_ref.HasField("trip"):
                            affected_trips.append(entity_ref.trip.trip_id)
                    
                    # Extract alert text
                    header_text = None
                    description_text = None
                    
                    for translation in alert_data.header_text.translation:
                        if translation.language == "en":
                            header_text = translation.text
                            break
                    
                    for translation in alert_data.description_text.translation:
                        if translation.language == "en":
                            description_text = translation.text
                            break
                    
                    alert = {
                        "alert_id": entity.id,
                        "alert_header_text": header_text,
                        "alert_description_text": description_text,
                        "alert_url": None,  # Not typically provided in GTFS-RT
                        "effective_start_date": effective_start_date,
                        "effective_end_date": effective_end_date,
                        "affected_routes": affected_routes,
                        "affected_stops": affected_stops,
                        "affected_trips": affected_trips,
                        "alert_severity_level": None,  # Not in GTFS-RT spec
                        "cause": None,  # Not in GTFS-RT spec
                        "effect": None,  # Not in GTFS-RT spec
                        "source": "mbta_gtfs_rt",
                        "feed_timestamp": self.feed_timestamps["alerts"],
                        "raw_entity": entity
                    }
                    
                    alerts.append(alert)
            
            self.logger.info(f"Parsed {len(alerts)} alerts from GTFS-RT")
            return alerts
            
        except Exception as e:
            self.logger.error(f"Error parsing alerts: {str(e)}", exc_info=True)
            return []
    
    async def fetch_data(self) -> List[Dict[str, Any]]:
        """Fetch all available GTFS-RT feeds."""
        all_data = []
        
        try:
            # Fetch vehicle positions
            vehicle_data = await self._fetch_protobuf_feed(self.endpoints["vehicle_positions"])
            if vehicle_data:
                vehicles = await self._parse_vehicle_positions(vehicle_data)
                all_data.extend(vehicles)
            
            # Fetch trip updates
            trip_update_data = await self._fetch_protobuf_feed(self.endpoints["trip_updates"])
            if trip_update_data:
                trip_updates = await self._parse_trip_updates(trip_update_data)
                all_data.extend(trip_updates)
            
            # Fetch alerts
            alert_data = await self._fetch_protobuf_feed(self.endpoints["alerts"])
            if alert_data:
                alerts = await self._parse_alerts(alert_data)
                all_data.extend(alerts)
            
            self.logger.info(f"Fetched {len(all_data)} total records from GTFS-RT feeds")
            
        except Exception as e:
            self.logger.error(f"Error fetching GTFS-RT data: {str(e)}", exc_info=True)
            raise
        
        return all_data
    
    async def transform_data(self, raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform raw GTFS-RT data into standardized format."""
        # Data is already transformed during parsing, just return as-is
        return raw_data
    
    async def get_feed_status(self) -> Dict[str, Any]:
        """Get the status of all GTFS-RT feeds."""
        status = {}
        
        for feed_name, timestamp in self.feed_timestamps.items():
            age_seconds = (datetime.utcnow() - timestamp).total_seconds()
            status[feed_name] = {
                "last_update": timestamp.isoformat(),
                "age_seconds": age_seconds,
                "age_minutes": age_seconds / 60,
                "sequence_number": self.feed_sequence_numbers.get(feed_name),
                "status": "fresh" if age_seconds < 300 else "stale" if age_seconds < 900 else "old"
            }
        
        return status
    
    async def validate_feed_freshness(self, max_age_minutes: int = 15) -> Dict[str, bool]:
        """Validate that feeds are fresh enough."""
        status = await self.get_feed_status()
        validation = {}
        
        for feed_name, feed_status in status.items():
            validation[feed_name] = feed_status["age_minutes"] <= max_age_minutes
        
        return validation
