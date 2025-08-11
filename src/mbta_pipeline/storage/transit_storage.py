"""Storage service for MBTA transit data and aggregations."""

from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta
import logging
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from ..models.transit import (
    Stop, Route, Trip, Prediction, VehiclePosition, TripUpdate, Alert
)
from ..models.database import (
    Stop as DBStop, Route as DBRoute, Trip as DBTrip, 
    Prediction as DBPrediction, VehiclePosition as DBVehiclePosition,
    TripUpdate as DBTripUpdate, Alert as DBAlert, DataIngestionLog,
    Vehicle as DBVehicle,
)
from .database import get_db_async, close_db_async
from ..config.settings import settings

logger = logging.getLogger(__name__)


class TransitStorageService:
    """Service for storing transit data and aggregations in the database."""
    
    def __init__(self):
        """Initialize the storage service."""
        self.logger = logger
    
    async def store_transit_data(self, data: Any, source_type: str = "unknown") -> Dict[str, Any]:
        """Store transit data in the database."""
        start_time = datetime.utcnow()
        data_type = type(data).__name__
        
        try:
            session = await get_db_async()
            try:
                if isinstance(data, Prediction):
                    result = await self._store_prediction(session, data)
                elif isinstance(data, VehiclePosition):
                    result = await self._store_vehicle_position(session, data)
                elif isinstance(data, TripUpdate):
                    result = await self._store_trip_update(session, data)
                elif isinstance(data, Alert):
                    result = await self._store_alert(session, data)
                elif isinstance(data, Route):
                    result = await self._store_route(session, data)
                elif isinstance(data, Stop):
                    result = await self._store_stop(session, data)
                elif isinstance(data, Trip):
                    result = await self._store_trip(session, data)
                else:
                    self.logger.warning(f"Unknown data type: {data_type}")
                    return {"success": False, "error": f"Unknown data type: {data_type}"}
                
                # Log successful ingestion
                await self._log_ingestion(
                    session, source_type, "success", 
                    1, 1, 0, 0, 
                    (datetime.utcnow() - start_time).total_seconds() * 1000
                )
                
                return {"success": True, "stored_id": result}
                
            finally:
                await close_db_async(session)
                
        except Exception as e:
            self.logger.error(f"Failed to store {data_type}: {str(e)}", exc_info=True)
            
            # Log failed ingestion
            try:
                session = await get_db_async()
                try:
                    await self._log_ingestion(
                        session, source_type, "error", 
                        1, 0, 0, 1, 
                        (datetime.utcnow() - start_time).total_seconds() * 1000,
                        error_message=str(e)
                    )
                finally:
                    await close_db_async(session)
            except Exception as log_error:
                self.logger.error(f"Failed to log ingestion error: {str(log_error)}")
            
            return {"success": False, "error": str(e)}
    
    async def store_aggregation_summary(self, summary: Dict[str, Any]) -> Dict[str, Any]:
        """Store aggregation summary statistics."""
        try:
            session = await get_db_async()
            try:
                # Store summary as a JSON field in a dedicated table
                # For now, we'll store it in the ingestion log with a special type
                await self._log_ingestion(
                    session, "aggregator", "success",
                    0, 0, 0, 0, 0,
                    error_details=summary
                )
                
                return {"success": True, "message": "Summary stored"}
                
            finally:
                await close_db_async(session)
                
        except Exception as e:
            self.logger.error(f"Failed to store aggregation summary: {str(e)}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    async def store_batch(self, data_list: List[Any], source_type: str = "unknown") -> Dict[str, Any]:
        """Store multiple transit data records in a batch."""
        start_time = datetime.utcnow()
        total_count = len(data_list)
        success_count = 0
        error_count = 0
        
        try:
            session = await get_db_async()
            try:
                for data in data_list:
                    try:
                        if isinstance(data, Prediction):
                            await self._store_prediction(session, data)
                        elif isinstance(data, VehiclePosition):
                            await self._store_vehicle_position(session, data)
                        elif isinstance(data, TripUpdate):
                            await self._store_trip_update(session, data)
                        elif isinstance(data, Alert):
                            await self._store_alert(session, data)
                        elif isinstance(data, Route):
                            await self._store_route(session, data)
                        elif isinstance(data, Stop):
                            await self._store_stop(session, data)
                        elif isinstance(data, Trip):
                            await self._store_trip(session, data)
                        
                        success_count += 1
                        
                    except Exception as e:
                        self.logger.error(f"Failed to store data item: {str(e)}")
                        error_count += 1
                
                # Log batch ingestion
                await self._log_ingestion(
                    session, source_type, "success" if error_count == 0 else "partial",
                    total_count, success_count, 0, error_count,
                    (datetime.utcnow() - start_time).total_seconds() * 1000
                )
                
                return {
                    "success": True,
                    "total": total_count,
                    "successful": success_count,
                    "errors": error_count
                }
                
            finally:
                await close_db_async(session)
                
        except Exception as e:
            self.logger.error(f"Failed to store batch: {str(e)}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    async def store_analytics_summary(self, analytics_summary: Dict[str, Any]) -> Dict[str, Any]:
        """Store analytics summary in the database."""
        try:
            session = await get_db_async()
            try:
                # Store analytics summary as a special type of ingestion log
                await self._log_ingestion(
                    session, 
                    "analytics", 
                    "success",
                    0, 0, 0, 0, 0,
                    error_details=analytics_summary
                )
                
                return {"success": True, "message": "Analytics summary stored"}
                
            finally:
                await close_db_async(session)
                
        except Exception as e:
            self.logger.error(f"Failed to store analytics summary: {str(e)}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def _store_prediction(self, session: Session, prediction: Prediction) -> str:
        """Store a prediction in the database."""
        # First ensure related entities exist
        await self._ensure_route_exists(session, prediction.route_id)
        await self._ensure_stop_exists(session, prediction.stop_id)
        await self._ensure_trip_exists(session, prediction.trip_id)
        if settings.auto_seed_missing_entities and getattr(prediction, 'vehicle_id', None):
            await self._ensure_vehicle_exists(session, prediction.vehicle_id, getattr(prediction, 'vehicle_label', None))
        
        # Idempotent insert: check existing by unique constraint fields
        existing = (
            session.query(DBPrediction)
            .filter(
                DBPrediction.trip_id == prediction.trip_id,
                DBPrediction.stop_id == prediction.stop_id,
                DBPrediction.arrival_time == prediction.arrival_time,
            )
            .first()
        )
        if existing:
            return str(existing.id)

        # Create database prediction record
        db_prediction = DBPrediction(
            trip_id=prediction.trip_id,
            route_id=prediction.route_id,
            stop_id=prediction.stop_id,
            vehicle_id=getattr(prediction, 'vehicle_id', None),
            arrival_time=prediction.arrival_time,
            departure_time=prediction.departure_time,
            schedule_relationship=self._map_schedule_relationship(
                getattr(prediction, 'schedule_relationship', None)
            ),
            status=getattr(prediction, 'status', None),
            delay=prediction.delay,
            timestamp=datetime.utcnow()
        )
        
        session.add(db_prediction)
        session.flush()  # Get the ID without committing
        
        return str(db_prediction.id)
    
    async def _store_vehicle_position(self, session: Session, position: VehiclePosition) -> str:
        """Store a vehicle position in the database."""
        # First ensure related entities exist
        if position.route_id:
            await self._ensure_route_exists(session, position.route_id)
        if position.trip_id:
            await self._ensure_trip_exists(session, position.trip_id)
        if hasattr(position, 'stop_id') and position.stop_id:
            await self._ensure_stop_exists(session, position.stop_id)
        if settings.auto_seed_missing_entities and getattr(position, 'vehicle_id', None):
            await self._ensure_vehicle_exists(session, position.vehicle_id)
        
        # Create database vehicle position record
        db_position = DBVehiclePosition(
            vehicle_id=position.vehicle_id,
            trip_id=getattr(position, 'trip_id', None),
            route_id=getattr(position, 'route_id', None),
            direction_id=getattr(position, 'direction_id', None),
            stop_id=getattr(position, 'stop_id', None),
            latitude=position.latitude,
            longitude=position.longitude,
            bearing=getattr(position, 'bearing', None),
            speed=getattr(position, 'speed', None),
            congestion_level=self._map_congestion_level(
                getattr(position, 'congestion_level', None)
            ),
            occupancy_status=self._map_occupancy_status(
                getattr(position, 'occupancy_status', None)
            ),
            timestamp=position.timestamp
        )
        
        session.add(db_position)
        session.flush()
        
        return str(db_position.id)
    
    async def _store_trip_update(self, session: Session, update: TripUpdate) -> str:
        """Store a trip update in the database."""
        # First ensure related entities exist
        await self._ensure_trip_exists(session, update.trip_id)
        if update.route_id:
            await self._ensure_route_exists(session, update.route_id)
        
        # Create database trip update record
        db_update = DBTripUpdate(
            trip_id=update.trip_id,
            route_id=getattr(update, 'route_id', None),
            delay=update.delay,
            start_time=getattr(update, 'start_time', None),
            end_time=getattr(update, 'end_time', None),
            timestamp=update.timestamp
        )
        
        session.add(db_update)
        session.flush()
        
        return str(db_update.id)
    
    async def _store_alert(self, session: Session, alert: Alert) -> str:
        """Store an alert in the database."""
        # Idempotent insert: check if alert already exists by alert_id
        existing = session.query(DBAlert).filter(DBAlert.alert_id == alert.alert_id).first()
        if existing:
            return str(existing.id)

        # Create database alert record
        db_alert = DBAlert(
            alert_id=alert.alert_id,
            alert_header_text=alert.alert_header_text,
            alert_description_text=alert.alert_description_text,
            alert_url=alert.alert_url,
            alert_effect=getattr(alert, 'effect', None),
            alert_severity_level=alert.alert_severity_level,
            affected_route_ids=alert.affected_routes,
            affected_stop_ids=alert.affected_stops,
            affected_trip_ids=alert.affected_trips,
            active_period_start=alert.effective_start_date,
            active_period_end=alert.effective_end_date,
            timestamp=datetime.utcnow()
        )
        
        session.add(db_alert)
        session.flush()
        
        return str(db_alert.id)
    
    async def _store_route(self, session: Session, route: Route) -> str:
        """Store a route in the database."""
        # Check if route already exists
        existing = session.query(DBRoute).filter(DBRoute.id == route.route_id).first()
        if existing:
            return existing.id
        
        # Create new route
        db_route = DBRoute(
            id=route.route_id,
            route_name=route.route_name,
            route_type=route.route_type,
            route_color=route.route_color,
            route_text_color=route.route_text_color
        )
        
        session.add(db_route)
        session.flush()
        
        return db_route.id
    
    async def _store_stop(self, session: Session, stop: Stop) -> str:
        """Store a stop in the database."""
        # Check if stop already exists
        existing = session.query(DBStop).filter(DBStop.id == stop.stop_id).first()
        if existing:
            return existing.id
        
        # Create new stop
        db_stop = DBStop(
            id=stop.stop_id,
            stop_name=stop.stop_name,
            stop_lat=stop.stop_lat,
            stop_lon=stop.stop_lon,
            wheelchair_boarding=stop.wheelchair_boarding
        )
        
        session.add(db_stop)
        session.flush()
        
        return db_stop.id
    
    async def _store_trip(self, session: Session, trip: Trip) -> str:
        """Store a trip in the database."""
        # Check if trip already exists
        existing = session.query(DBTrip).filter(DBTrip.id == trip.trip_id).first()
        if existing:
            return existing.id
        
        # First ensure route exists
        await self._ensure_route_exists(session, trip.route_id)
        
        # Create new trip
        db_trip = DBTrip(
            id=trip.trip_id,
            route_id=trip.route_id,
            service_id=trip.service_id,
            trip_headsign=trip.trip_headsign,
            trip_short_name=trip.trip_short_name,
            direction_id=trip.direction_id,
            block_id=getattr(trip, 'block_id', None),
            shape_id=getattr(trip, 'shape_id', None),
            wheelchair_accessible=getattr(trip, 'wheelchair_accessible', None),
            bikes_allowed=getattr(trip, 'bikes_allowed', None)
        )
        
        session.add(db_trip)
        session.flush()
        
        return db_trip.id
    
    async def _ensure_route_exists(self, session: Session, route_id: str) -> None:
        """Ensure a route exists in the database."""
        if not session.query(DBRoute).filter(DBRoute.id == route_id).first():
            # Create a minimal route record
            db_route = DBRoute(
                id=route_id,
                route_name=f"Route {route_id}",
                route_type=0  # Default to tram
            )
            session.add(db_route)
            session.flush()
    
    async def _ensure_stop_exists(self, session: Session, stop_id: str) -> None:
        """Ensure a stop exists in the database."""
        if not session.query(DBStop).filter(DBStop.id == stop_id).first():
            # Create a minimal stop record
            db_stop = DBStop(
                id=stop_id,
                stop_name=f"Stop {stop_id}"
            )
            session.add(db_stop)
            session.flush()
    
    async def _ensure_trip_exists(self, session: Session, trip_id: str) -> None:
        """Ensure a trip exists in the database."""
        if not session.query(DBTrip).filter(DBTrip.id == trip_id).first():
            # Create a minimal trip record
            db_trip = DBTrip(
                id=trip_id,
                route_id="unknown",  # Will be updated when we have route info
                service_id="unknown"
            )
            session.add(db_trip)
            session.flush()

    async def _ensure_vehicle_exists(self, session: Session, vehicle_id: str, vehicle_label: Optional[str] = None) -> None:
        """Ensure a vehicle exists in the database."""
        if vehicle_id and not session.query(DBVehicle).filter(DBVehicle.vehicle_id == vehicle_id).first():
            db_vehicle = DBVehicle(
                id=vehicle_id,
                vehicle_id=vehicle_id,
                vehicle_label=vehicle_label,
            )
            session.add(db_vehicle)
            session.flush()
    
    async def _log_ingestion(
        self, 
        session: Session, 
        source_type: str, 
        status: str, 
        records_processed: int,
        records_inserted: int,
        records_updated: int,
        records_failed: int,
        processing_time_ms: float,
        error_message: Optional[str] = None,
        error_details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log ingestion activity."""
        # Ensure error_details is JSON-serializable (coerce datetimes)
        def _sanitize(obj):
            from datetime import datetime as _dt, date as _date
            if isinstance(obj, dict):
                return {k: _sanitize(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [_sanitize(v) for v in obj]
            if isinstance(obj, (_dt, _date)):
                return obj.isoformat()
            return obj

        log_entry = DataIngestionLog(
            source_type=source_type,
            status=status,
            records_processed=records_processed,
            records_inserted=records_inserted,
            records_updated=records_updated,
            records_failed=records_failed,
            processing_time_ms=int(processing_time_ms),
            error_message=error_message,
            error_details=_sanitize(error_details) if error_details is not None else None,
            started_at=datetime.utcnow() - timedelta(milliseconds=processing_time_ms),
            completed_at=datetime.utcnow()
        )
        
        session.add(log_entry)
        session.flush()

    # ---------------------
    # Mapping helpers
    # ---------------------
    def _map_schedule_relationship(self, value: Optional[Union[str, int]]) -> Optional[int]:
        if value is None:
            return None
        if isinstance(value, int):
            return value
        mapping = {
            'scheduled': 0,
            'added': 1,
            'unscheduled': 2,
            'canceled': 3,
            'skipped': 4,
        }
        return mapping.get(str(value).lower(), None)

    def _map_congestion_level(self, value: Optional[Union[str, int]]) -> Optional[int]:
        if value is None:
            return None
        if isinstance(value, int):
            return value
        mapping = {
            'unknown': 0,
            'smooth': 1,
            'low': 1,
            'moderate': 2,
            'medium': 2,
            'severe': 3,
            'heavy': 3,
        }
        return mapping.get(str(value).lower(), None)

    def _map_occupancy_status(self, value: Optional[Union[str, int]]) -> Optional[int]:
        if value is None:
            return None
        if isinstance(value, int):
            return value
        mapping = {
            'empty': 0,
            'many_seats_available': 1,
            'few_seats_available': 2,
            'standing_room_only': 3,
            'crushed_standing_room_only': 4,
            'full': 5,
            'not_accepting_passengers': 6,
        }
        return mapping.get(str(value).lower(), None)
    
    async def get_recent_predictions(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent predictions from the database."""
        try:
            session = await get_db_async()
            try:
                predictions = session.query(DBPrediction)\
                    .order_by(DBPrediction.timestamp.desc())\
                    .limit(limit)\
                    .all()
                
                return [
                    {
                        "id": str(p.id),
                        "trip_id": p.trip_id,
                        "route_id": p.route_id,
                        "stop_id": p.stop_id,
                        "arrival_time": p.arrival_time.isoformat() if p.arrival_time else None,
                        "delay": p.delay,
                        "timestamp": p.timestamp.isoformat()
                    }
                    for p in predictions
                ]
                
            finally:
                await close_db_async(session)
                
        except Exception as e:
            self.logger.error(f"Failed to get recent predictions: {str(e)}", exc_info=True)
            return []
    
    async def get_service_health_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get service health summary from stored data."""
        try:
            session = await get_db_async()
            try:
                cutoff_time = datetime.utcnow() - timedelta(hours=hours)
                
                # Get predictions in time window
                predictions = session.query(DBPrediction)\
                    .filter(DBPrediction.timestamp >= cutoff_time)\
                    .all()
                
                # Calculate metrics
                total_predictions = len(predictions)
                delayed_predictions = sum(1 for p in predictions if p.delay and p.delay > 0)
                delay_percentage = (delayed_predictions / total_predictions * 100) if total_predictions > 0 else 0
                
                # Get recent alerts
                alerts = session.query(DBAlert)\
                    .filter(DBAlert.timestamp >= cutoff_time)\
                    .all()
                
                return {
                    "time_window_hours": hours,
                    "total_predictions": total_predictions,
                    "delayed_predictions": delayed_predictions,
                    "delay_percentage": round(delay_percentage, 2),
                    "total_alerts": len(alerts),
                    "timestamp": datetime.utcnow().isoformat()
                }
                
            finally:
                await close_db_async(session)
                
        except Exception as e:
            self.logger.error(f"Failed to get service health summary: {str(e)}", exc_info=True)
            return {"error": str(e)}


# Global storage service instance
transit_storage = TransitStorageService()
