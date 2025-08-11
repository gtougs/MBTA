"""MBTA V3 REST API ingestor for predictions and vehicle data."""

import asyncio
import aiohttp
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import json

from .base import BaseIngestor
from ..config.settings import settings
from ..models.transit import Prediction, VehiclePosition
from ..utils.logging import get_logger


class V3RestIngestor(BaseIngestor):
    """Ingestor for MBTA V3 REST API data."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the V3 REST ingestor."""
        super().__init__("mbta_v3_rest", config)
        
        # API configuration
        self.api_key = settings.mbta_api_key
        self.base_url = settings.mbta_base_url
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Endpoints
        self.endpoints = {
            "predictions": "/predictions",
            "vehicles": "/vehicles",
            "routes": "/routes",
            "stops": "/stops",
            "trips": "/trips"
        }
        
        # Rate limiting
        self.rate_limit_requests_per_minute = settings.mbta_rate_limit_requests_per_minute
        self.rate_limit_burst_size = settings.mbta_rate_limit_burst_size
        self.request_timestamps = []
        
        self.logger = get_logger(f"{self.__class__.__name__}")
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "User-Agent": "MBTA-Data-Pipeline/1.0",
                "Accept": "application/json"
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
                    "Authorization": f"Bearer {self.api_key}",
                    "User-Agent": "MBTA-Data-Pipeline/1.0",
                    "Accept": "application/json"
                }
            )
    
    async def _check_rate_limit(self) -> None:
        """Check and enforce rate limiting."""
        now = datetime.utcnow()
        cutoff = now - timedelta(minutes=1)
        
        # Remove old timestamps
        self.request_timestamps = [ts for ts in self.request_timestamps if ts > cutoff]
        
        # Check if we're at the limit
        if len(self.request_timestamps) >= self.rate_limit_requests_per_minute:
            wait_time = (self.request_timestamps[0] - cutoff).total_seconds()
            self.logger.warning(f"Rate limit reached, waiting {wait_time:.2f} seconds")
            await asyncio.sleep(wait_time)
        
        # Add current timestamp
        self.request_timestamps.append(now)
    
    async def _make_request(
        self, 
        endpoint: str, 
        params: Optional[Dict[str, Any]] = None,
        retries: int = 0
    ) -> Dict[str, Any]:
        """Make a rate-limited request to the MBTA API."""
        await self._check_rate_limit()
        
        url = f"{self.base_url}{endpoint}"
        params = params or {}
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    self.logger.debug(f"Successful request to {endpoint}: {len(data.get('data', []))} records")
                    return data
                elif response.status == 429:  # Rate limited
                    retry_after = int(response.headers.get('Retry-After', 60))
                    self.logger.warning(f"Rate limited, retrying after {retry_after} seconds")
                    await asyncio.sleep(retry_after)
                    return await self._make_request(endpoint, params, retries + 1)
                elif response.status >= 500 and retries < self.max_retries:
                    self.logger.warning(f"Server error {response.status}, retrying...")
                    await asyncio.sleep(self.retry_delay * (2 ** retries))
                    return await self._make_request(endpoint, params, retries + 1)
                else:
                    response.raise_for_status()
                    
        except aiohttp.ClientError as e:
            if retries < self.max_retries:
                self.logger.warning(f"Request failed, retrying... Error: {str(e)}")
                await asyncio.sleep(self.retry_delay * (2 ** retries))
                return await self._make_request(endpoint, params, retries + 1)
            else:
                raise
    
    async def fetch_predictions(
        self, 
        route_ids: Optional[List[str]] = None,
        stop_ids: Optional[List[str]] = None,
        include: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Fetch predictions from the MBTA V3 API."""
        params = {}
        
        if route_ids:
            params["filter[route]"] = ",".join(route_ids)
        if stop_ids:
            params["filter[stop]"] = ",".join(stop_ids)
        if include:
            params["include"] = ",".join(include)
        
        # Always include related entities for better data quality
        if "include" not in params:
            params["include"] = "stop,trip,route"
        
        data = await self._make_request(self.endpoints["predictions"], params)
        return data.get("data", [])
    
    async def fetch_vehicles(
        self, 
        route_ids: Optional[List[str]] = None,
        include: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Fetch vehicle positions from the MBTA V3 API."""
        params = {}
        
        if route_ids:
            params["filter[route]"] = ",".join(route_ids)
        if include:
            params["include"] = ",".join(include)
        
        # Include route information
        if "include" not in params:
            params["include"] = "route"
        
        data = await self._make_request(self.endpoints["vehicles"], params)
        return data.get("data", [])
    
    async def fetch_routes(self, route_types: Optional[List[int]] = None) -> List[Dict[str, Any]]:
        """Fetch route information from the MBTA V3 API."""
        params = {}
        
        if route_types:
            params["filter[type]"] = ",".join(map(str, route_types))
        
        data = await self._make_request(self.endpoints["routes"], params)
        return data.get("data", [])
    
    async def fetch_data(self) -> List[Dict[str, Any]]:
        """Fetch all available data from the V3 API."""
        all_data = []
        
        try:
            # Fetch predictions for major routes
            major_routes = ["Red", "Orange", "Blue", "Green-B", "Green-C", "Green-D", "Green-E"]
            predictions = await self.fetch_predictions(
                route_ids=major_routes,
                include=["stop", "trip", "route"]
            )
            all_data.extend(predictions)
            
            # Fetch vehicle positions
            vehicles = await self.fetch_vehicles(
                route_ids=major_routes,
                include=["route"]
            )
            all_data.extend(vehicles)
            
            self.logger.info(f"Fetched {len(predictions)} predictions and {len(vehicles)} vehicles")
            
        except Exception as e:
            self.logger.error(f"Error fetching V3 API data: {str(e)}", exc_info=True)
            raise
        
        return all_data
    
    async def transform_data(self, raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform raw V3 API data into standardized format."""
        transformed_data = []
        
        for item in raw_data:
            try:
                item_type = item.get("type")
                
                if item_type == "prediction":
                    transformed = await self._transform_prediction(item)
                elif item_type == "vehicle":
                    transformed = await self._transform_vehicle(item)
                else:
                    self.logger.warning(f"Unknown item type: {item_type}")
                    continue
                
                if transformed:
                    transformed_data.append(transformed)
                    
            except Exception as e:
                self.logger.error(f"Error transforming item: {str(e)}", exc_info=True)
                continue
        
        return transformed_data
    
    async def _transform_prediction(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Transform a prediction item."""
        try:
            attributes = item.get("attributes", {})
            relationships = item.get("relationships", {})
            
            # Extract related entities
            stop_data = relationships.get("stop", {}).get("data", {})
            trip_data = relationships.get("trip", {}).get("data", {})
            route_data = relationships.get("route", {}).get("data", {})
            
            # Parse timestamps
            arrival_time = None
            departure_time = None
            
            if attributes.get("arrival_time"):
                arrival_time = datetime.fromisoformat(attributes["arrival_time"].replace("Z", "+00:00"))
            if attributes.get("departure_time"):
                departure_time = datetime.fromisoformat(attributes["departure_time"].replace("Z", "+00:00"))
            
            transformed = {
                "prediction_id": item["id"],
                "trip_id": trip_data.get("id"),
                "stop_id": stop_data.get("id"),
                "route_id": route_data.get("id"),
                "arrival_time": arrival_time,
                "departure_time": departure_time,
                "schedule_relationship": attributes.get("schedule_relationship"),
                "vehicle_id": attributes.get("vehicle", {}).get("id"),
                "vehicle_label": attributes.get("vehicle", {}).get("label"),
                "status": attributes.get("status"),
                "delay": attributes.get("delay"),
                "source": "mbta_v3_api",
                "raw_data": item
            }
            
            return transformed
            
        except Exception as e:
            self.logger.error(f"Error transforming prediction: {str(e)}", exc_info=True)
            return None
    
    async def _transform_vehicle(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Transform a vehicle item."""
        try:
            attributes = item.get("attributes", {})
            relationships = item.get("relationships", {})
            
            # Extract route information
            route_data = relationships.get("route", {}).get("data", {})
            
            # Parse timestamp
            timestamp = None
            if attributes.get("updated_at"):
                timestamp = datetime.fromisoformat(attributes["updated_at"].replace("Z", "+00:00"))
            
            transformed = {
                "vehicle_id": item["id"],
                "trip_id": attributes.get("trip", {}).get("id"),
                "route_id": route_data.get("id"),
                "latitude": attributes.get("latitude"),
                "longitude": attributes.get("longitude"),
                "bearing": attributes.get("bearing"),
                "speed": attributes.get("speed"),
                "current_status": attributes.get("current_status"),
                "timestamp": timestamp,
                "congestion_level": attributes.get("congestion_level"),
                "occupancy_status": attributes.get("occupancy_status"),
                "source": "mbta_v3_api",
                "raw_data": item
            }
            
            return transformed
            
        except Exception as e:
            self.logger.error(f"Error transforming vehicle: {str(e)}", exc_info=True)
            return None
    
    async def get_route_summary(self) -> Dict[str, Any]:
        """Get a summary of available routes."""
        try:
            routes = await self.fetch_routes()
            route_summary = {}
            
            for route in routes:
                route_id = route["id"]
                attributes = route.get("attributes", {})
                route_summary[route_id] = {
                    "name": attributes.get("long_name", route_id),
                    "type": attributes.get("type"),
                    "color": attributes.get("color"),
                    "text_color": attributes.get("text_color")
                }
            
            return route_summary
            
        except Exception as e:
            self.logger.error(f"Error getting route summary: {str(e)}", exc_info=True)
            return {}
