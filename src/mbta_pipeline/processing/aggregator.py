"""Data aggregator for combining and summarizing MBTA transit data."""

from typing import Any, Dict, List, Optional, Union, Counter
from datetime import datetime, timedelta
from collections import defaultdict
import logging

from .base import BaseProcessor
from ..models.transit import (
    Stop, Route, Trip, Prediction, 
    VehiclePosition, TripUpdate, Alert
)
from ..storage.transit_storage import transit_storage

logger = logging.getLogger(__name__)


class DataAggregator(BaseProcessor):
    """Aggregates transit data for analysis and reporting."""
    
    def __init__(self):
        """Initialize the data aggregator."""
        super().__init__("DataAggregator")
        self.aggregations = defaultdict(list)
        self.summary_stats = {}
        self.storage_enabled = True
        self.batch_size = 100  # Process data in batches for storage
    
    def process(self, data: Any) -> Any:
        """Process data for aggregation and storage."""
        # Store data for aggregation
        data_type = type(data).__name__
        self.aggregations[data_type].append(data)
        
        # Update summary statistics
        self._update_summary_stats(data_type, data)
        
        return data
    
    async def process_and_store(self, data: Any) -> Dict[str, Any]:
        """Process data for aggregation and store it in the database."""
        # Process for aggregation
        self.process(data)
        
        # Store data in database if storage is enabled
        if self.storage_enabled:
            try:
                data_type = type(data).__name__
                storage_result = await transit_storage.store_transit_data(
                    data, 
                    source_type=f"aggregator_{data_type.lower()}"
                )
                
                if not storage_result["success"]:
                    logger.warning(f"Failed to store {data_type}: {storage_result.get('error', 'Unknown error')}")
                
                return storage_result
                
            except Exception as e:
                logger.error(f"Storage error for {type(data).__name__}: {str(e)}", exc_info=True)
                return {"success": False, "error": str(e)}
        
        return {"success": True, "message": "Storage disabled"}
    
    async def process_batch(self, data_list: List[Any], source_type: str = "unknown") -> Dict[str, Any]:
        """Process and store a batch of data records."""
        if not data_list:
            return {"success": True, "total": 0, "processed": 0}
        
        # Process each item for aggregation
        for data in data_list:
            self.process(data)
        
        # Store batch in database if storage is enabled
        if self.storage_enabled:
            try:
                storage_result = await transit_storage.store_batch(data_list, source_type)
                return {
                    "success": True,
                    "total": len(data_list),
                    "processed": len(data_list),
                    "storage_result": storage_result
                }
            except Exception as e:
                logger.error(f"Batch storage error: {str(e)}", exc_info=True)
                return {
                    "success": False,
                    "total": len(data_list),
                    "processed": len(data_list),
                    "error": str(e)
                }
        
        return {"success": True, "total": len(data_list), "processed": len(data_list)}
    
    async def store_aggregation_summary(self) -> Dict[str, Any]:
        """Store current aggregation summary in the database."""
        try:
            summary = self.get_summary_stats()
            result = await transit_storage.store_aggregation_summary(summary)
            
            if result["success"]:
                logger.info("Aggregation summary stored successfully")
            else:
                logger.warning(f"Failed to store aggregation summary: {result.get('error', 'Unknown error')}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error storing aggregation summary: {str(e)}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    async def get_stored_service_health(self, hours: int = 24) -> Dict[str, Any]:
        """Get service health summary from stored data."""
        try:
            return await transit_storage.get_service_health_summary(hours)
        except Exception as e:
            logger.error(f"Error getting stored service health: {str(e)}", exc_info=True)
            return {"error": str(e)}
    
    async def get_stored_recent_predictions(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent predictions from stored data."""
        try:
            return await transit_storage.get_recent_predictions(limit)
        except Exception as e:
            logger.error(f"Error getting stored predictions: {str(e)}", exc_info=True)
            return []
    
    async def store_analytics_summary(self, analytics_summary: Dict[str, Any]) -> Dict[str, Any]:
        """Store analytics summary in the database."""
        try:
            from ..storage.transit_storage import transit_storage
            
            # Store analytics summary through transit storage
            result = await transit_storage.store_analytics_summary(analytics_summary)
            
            if result["success"]:
                logger.info("Analytics summary stored successfully")
            else:
                logger.warning(f"Failed to store analytics summary: {result.get('error', 'Unknown error')}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error storing analytics summary: {str(e)}", exc_info=True)
            return {"success": False, "error": str(e)}

    def enable_storage(self, enabled: bool = True) -> None:
        """Enable or disable data storage."""
        self.storage_enabled = enabled
        logger.info(f"Data storage {'enabled' if enabled else 'disabled'}")
    
    def set_batch_size(self, size: int) -> None:
        """Set the batch size for processing."""
        if size > 0:
            self.batch_size = size
            logger.info(f"Batch size set to {size}")
        else:
            logger.warning("Batch size must be positive")
    
    def get_aggregations(self, data_type: Optional[str] = None) -> Dict[str, Any]:
        """Get aggregated data by type or all types."""
        if data_type:
            return {data_type: self.aggregations.get(data_type, [])}
        return dict(self.aggregations)
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """Get comprehensive summary statistics."""
        return {
            "timestamp": datetime.now().isoformat(),
            "total_records": sum(len(records) for records in self.aggregations.values()),
            "by_type": self._get_type_summary(),
            "service_metrics": self._get_service_metrics(),
            "performance_metrics": self._get_performance_metrics(),
            "alert_summary": self._get_alert_summary(),
            "geographic_summary": self._get_geographic_summary()
        }
    
    def get_route_summary(self) -> Dict[str, Any]:
        """Get summary statistics by route."""
        route_stats = defaultdict(lambda: {
            "predictions": 0,
            "delays": [],
            "vehicle_positions": 0,
            "alerts": 0
        })
        
        # Aggregate by route
        for prediction in self.aggregations.get("Prediction", []):
            route_stats[prediction.route_id]["predictions"] += 1
            if prediction.delay:
                route_stats[prediction.route_id]["delays"].append(prediction.delay)
        
        for position in self.aggregations.get("VehiclePosition", []):
            if position.route_id:
                route_stats[position.route_id]["vehicle_positions"] += 1
        
        for alert in self.aggregations.get("Alert", []):
            for route_id in alert.affected_routes:
                route_stats[route_id]["alerts"] += 1
        
        # Calculate averages
        for route_id, stats in route_stats.items():
            if stats["delays"]:
                stats["avg_delay"] = sum(stats["delays"]) / len(stats["delays"])
                stats["max_delay"] = max(stats["delays"])
                stats["min_delay"] = min(stats["delays"])
            else:
                stats["avg_delay"] = 0
                stats["max_delay"] = 0
                stats["min_delay"] = 0
        
        return dict(route_stats)
    
    def get_stop_summary(self) -> Dict[str, Any]:
        """Get summary statistics by stop."""
        stop_stats = defaultdict(lambda: {
            "predictions": 0,
            "delays": [],
            "alerts": 0
        })
        
        # Aggregate by stop
        for prediction in self.aggregations.get("Prediction", []):
            stop_stats[prediction.stop_id]["predictions"] += 1
            if prediction.delay:
                stop_stats[prediction.stop_id]["delays"].append(prediction.delay)
        
        for alert in self.aggregations.get("Alert", []):
            for stop_id in alert.affected_stops:
                stop_stats[stop_id]["alerts"] += 1
        
        # Calculate averages
        for stop_id, stats in stop_stats.items():
            if stats["delays"]:
                stats["avg_delay"] = sum(stats["delays"]) / len(stats["delays"])
                stats["max_delay"] = max(stats["delays"])
                stats["min_delay"] = min(stats["delays"])
            else:
                stats["avg_delay"] = 0
                stats["max_delay"] = 0
                stats["min_delay"] = 0
        
        return dict(stop_stats)
    
    def get_time_based_summary(self, time_window: timedelta = timedelta(hours=1)) -> Dict[str, Any]:
        """Get summary statistics for a specific time window."""
        now = datetime.now()
        cutoff_time = now - time_window
        
        time_stats = {
            "time_window": str(time_window),
            "start_time": cutoff_time.isoformat(),
            "end_time": now.isoformat(),
            "predictions": 0,
            "vehicle_positions": 0,
            "trip_updates": 0,
            "alerts": 0,
            "delays": []
        }
        
        # Filter data by time window
        for prediction in self.aggregations.get("Prediction", []):
            if prediction.arrival_time and prediction.arrival_time >= cutoff_time:
                time_stats["predictions"] += 1
                if prediction.delay:
                    time_stats["delays"].append(prediction.delay)
        
        for position in self.aggregations.get("VehiclePosition", []):
            if position.timestamp >= cutoff_time:
                time_stats["vehicle_positions"] += 1
        
        for update in self.aggregations.get("TripUpdate", []):
            if update.timestamp >= cutoff_time:
                time_stats["trip_updates"] += 1
        
        for alert in self.aggregations.get("Alert", []):
            if (alert.effective_start_date and alert.effective_start_date >= cutoff_time) or \
               (alert.effective_end_date and alert.effective_end_date >= cutoff_time):
                time_stats["alerts"] += 1
        
        # Calculate delay statistics
        if time_stats["delays"]:
            time_stats["avg_delay"] = sum(time_stats["delays"]) / len(time_stats["delays"])
            time_stats["max_delay"] = max(time_stats["delays"])
            time_stats["min_delay"] = min(time_stats["delays"])
        else:
            time_stats["avg_delay"] = 0
            time_stats["max_delay"] = 0
            time_stats["min_delay"] = 0
        
        return time_stats
    
    def get_service_health_summary(self) -> Dict[str, Any]:
        """Get overall service health summary."""
        total_predictions = len(self.aggregations.get("Prediction", []))
        total_vehicles = len(self.aggregations.get("VehiclePosition", []))
        total_alerts = len(self.aggregations.get("Alert", []))
        
        # Calculate delay percentages
        delayed_predictions = sum(
            1 for p in self.aggregations.get("Prediction", [])
            if p.delay and p.delay > 0
        )
        
        delay_percentage = (
            (delayed_predictions / total_predictions * 100)
            if total_predictions > 0 else 0
        )
        
        # Categorize delays
        minor_delays = sum(
            1 for p in self.aggregations.get("Prediction", [])
            if p.delay and 0 < p.delay <= 300  # 5 minutes
        )
        
        moderate_delays = sum(
            1 for p in self.aggregations.get("Prediction", [])
            if p.delay and 300 < p.delay <= 900  # 15 minutes
        )
        
        major_delays = sum(
            1 for p in self.aggregations.get("Prediction", [])
            if p.delay and p.delay > 900  # 15+ minutes
        )
        
        return {
            "timestamp": datetime.now().isoformat(),
            "total_predictions": total_predictions,
            "total_vehicles": total_vehicles,
            "total_alerts": total_alerts,
            "delay_percentage": round(delay_percentage, 2),
            "delay_breakdown": {
                "minor": minor_delays,
                "moderate": moderate_delays,
                "major": major_delays
            },
            "service_status": self._get_overall_service_status(delay_percentage, total_alerts)
        }
    
    def _update_summary_stats(self, data_type: str, data: Any):
        """Update summary statistics for a data type."""
        if data_type not in self.summary_stats:
            self.summary_stats[data_type] = {
                "count": 0,
                "first_seen": datetime.now(),
                "last_seen": datetime.now()
            }
        
        self.summary_stats[data_type]["count"] += 1
        self.summary_stats[data_type]["last_seen"] = datetime.now()
    
    def _get_type_summary(self) -> Dict[str, Any]:
        """Get summary by data type."""
        return {
            data_type: {
                "count": len(records),
                "first_seen": min((r.timestamp if hasattr(r, 'timestamp') else datetime.now() for r in records), default=datetime.now()),
                "last_seen": max((r.timestamp if hasattr(r, 'timestamp') else datetime.now() for r in records), default=datetime.now())
            }
            for data_type, records in self.aggregations.items()
        }
    
    def _get_service_metrics(self) -> Dict[str, Any]:
        """Get service-related metrics."""
        predictions = self.aggregations.get("Prediction", [])
        vehicles = self.aggregations.get("VehiclePosition", [])
        
        return {
            "total_predictions": len(predictions),
            "total_vehicles": len(vehicles),
            "active_routes": len(set(p.route_id for p in predictions)),
            "active_stops": len(set(p.stop_id for p in predictions)),
            "delayed_predictions": sum(1 for p in predictions if p.delay and p.delay > 0)
        }
    
    def _get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance-related metrics."""
        predictions = self.aggregations.get("Prediction", [])
        delays = [p.delay for p in predictions if p.delay is not None]
        
        if not delays:
            return {"avg_delay": 0, "max_delay": 0, "min_delay": 0}
        
        return {
            "avg_delay": sum(delays) / len(delays),
            "max_delay": max(delays),
            "min_delay": min(delays),
            "delay_count": len(delays)
        }
    
    def _get_alert_summary(self) -> Dict[str, Any]:
        """Get alert summary."""
        alerts = self.aggregations.get("Alert", [])
        
        severity_counts = Counter(
            alert.alert_severity_level for alert in alerts 
            if alert.alert_severity_level
        )
        
        return {
            "total_alerts": len(alerts),
            "by_severity": dict(severity_counts),
            "active_alerts": len([a for a in alerts if self._is_alert_active(a)])
        }
    
    def _get_geographic_summary(self) -> Dict[str, Any]:
        """Get geographic summary."""
        stops = self.aggregations.get("Stop", [])
        vehicles = self.aggregations.get("VehiclePosition", [])
        
        regions = defaultdict(int)
        for stop in stops:
            if hasattr(stop, 'metadata') and stop.metadata and 'geographic_region' in stop.metadata:
                regions[stop.metadata['geographic_region']] += 1
        
        return {
            "total_stops": len(stops),
            "total_vehicles": len(vehicles),
            "by_region": dict(regions)
        }
    
    def _get_overall_service_status(self, delay_percentage: float, total_alerts: int) -> str:
        """Determine overall service status."""
        if delay_percentage > 20 or total_alerts > 10:
            return "poor"
        elif delay_percentage > 10 or total_alerts > 5:
            return "fair"
        elif delay_percentage > 5 or total_alerts > 2:
            return "good"
        else:
            return "excellent"
    
    def _is_alert_active(self, alert: Alert) -> bool:
        """Check if an alert is currently active."""
        now = datetime.now()
        
        if alert.effective_start_date and alert.effective_start_date > now:
            return False
        
        if alert.effective_end_date and alert.effective_end_date < now:
            return False
        
        return True
    
    def clear_aggregations(self):
        """Clear all aggregated data."""
        self.aggregations.clear()
        self.summary_stats.clear()
        logger.info("Cleared all aggregated data")
    
    def export_aggregations(self, format: str = "json") -> str:
        """Export aggregations in specified format."""
        if format.lower() == "json":
            import json
            return json.dumps(self.get_summary_stats(), default=str, indent=2)
        else:
            raise ValueError(f"Unsupported export format: {format}")
