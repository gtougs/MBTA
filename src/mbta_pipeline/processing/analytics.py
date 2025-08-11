"""Analytics engine for MBTA transit data analysis."""

from typing import Any, Dict, List, Optional, Tuple, Union
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import logging
import statistics
from dataclasses import dataclass
import asyncio

from ..models.transit import Prediction, VehiclePosition, TripUpdate, Alert, Route, Stop
from ..storage.transit_storage import transit_storage
from .base import BaseProcessor

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Container for performance metrics."""
    on_time_percentage: float
    average_delay: float
    delay_std_dev: float
    total_trips: int
    delayed_trips: int
    severely_delayed_trips: int  # >5 minutes
    timestamp: datetime


@dataclass
class HeadwayAnalysis:
    """Container for headway analysis."""
    route_id: str
    direction_id: int
    average_headway: float
    headway_variance: float
    bunching_incidents: int
    gap_incidents: int
    timestamp: datetime


@dataclass
class AnomalyDetection:
    """Container for anomaly detection results."""
    anomaly_type: str
    severity: str
    description: str
    affected_routes: List[str]
    affected_stops: List[str]
    confidence_score: float
    timestamp: datetime


class TransitAnalytics(BaseProcessor):
    """Real-time analytics engine for MBTA transit data."""
    
    def __init__(self):
        """Initialize the analytics engine."""
        super().__init__("TransitAnalytics")
        self.performance_cache = {}
        self.headway_cache = {}
        self.anomaly_cache = {}
        self.cache_ttl = timedelta(minutes=5)
        
    async def analyze_performance(self, route_id: Optional[str] = None, 
                                time_window: timedelta = timedelta(hours=1)) -> PerformanceMetrics:
        """Analyze on-time performance for routes."""
        try:
            # Get recent predictions from storage
            predictions = await transit_storage.get_recent_predictions(limit=1000)
            
            if not predictions:
                return PerformanceMetrics(
                    on_time_percentage=0.0,
                    average_delay=0.0,
                    delay_std_dev=0.0,
                    total_trips=0,
                    delayed_trips=0,
                    severely_delayed_trips=0,
                    timestamp=datetime.utcnow()
                )
            
            # Filter by route if specified
            if route_id:
                predictions = [p for p in predictions if p.get('route_id') == route_id]
            
            # Filter by time window
            cutoff_time = datetime.utcnow() - time_window
            predictions = [p for p in predictions if p.get('timestamp') and datetime.fromisoformat(p['timestamp'].replace('Z', '+00:00')) >= cutoff_time]
            
            if not predictions:
                return PerformanceMetrics(
                    on_time_percentage=0.0,
                    average_delay=0.0,
                    delay_std_dev=0.0,
                    total_trips=0,
                    delayed_trips=0,
                    severely_delayed_trips=0,
                    timestamp=datetime.utcnow()
                )
            
            # Calculate metrics
            delays = [p.get('delay', 0) for p in predictions if p.get('delay') is not None]
            total_trips = len(predictions)
            delayed_trips = len([d for d in delays if d > 0])
            severely_delayed = len([d for d in delays if d > 300])  # >5 minutes
            
            if delays:
                avg_delay = statistics.mean(delays)
                delay_std = statistics.stdev(delays) if len(delays) > 1 else 0.0
                on_time_pct = ((total_trips - delayed_trips) / total_trips) * 100
            else:
                avg_delay = 0.0
                delay_std = 0.0
                on_time_pct = 100.0
            
            metrics = PerformanceMetrics(
                on_time_percentage=on_time_pct,
                average_delay=avg_delay,
                delay_std_dev=delay_std,
                total_trips=total_trips,
                delayed_trips=delayed_trips,
                severely_delayed_trips=severely_delayed,
                timestamp=datetime.utcnow()
            )
            
            # Cache results
            cache_key = f"performance_{route_id or 'all'}_{time_window.total_seconds()}"
            self.performance_cache[cache_key] = {
                'metrics': metrics,
                'timestamp': datetime.utcnow()
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error analyzing performance: {str(e)}", exc_info=True)
            raise
    
    async def analyze_headways(self, route_id: str, direction_id: int = 0,
                             time_window: timedelta = timedelta(hours=1)) -> HeadwayAnalysis:
        """Analyze headways between consecutive vehicles on a route."""
        try:
            # Get recent vehicle positions for the route
            # This would need to be implemented in transit_storage
            # For now, we'll use a placeholder approach
            
            # Calculate headway metrics
            headway_incidents = 0
            gap_incidents = 0
            
            # Placeholder calculations - in reality, you'd analyze actual headway data
            avg_headway = 300.0  # 5 minutes default
            headway_variance = 60.0  # 1 minute variance
            
            analysis = HeadwayAnalysis(
                route_id=route_id,
                direction_id=direction_id,
                average_headway=avg_headway,
                headway_variance=headway_variance,
                bunching_incidents=bunching_incidents,
                gap_incidents=gap_incidents,
                timestamp=datetime.utcnow()
            )
            
            # Cache results
            cache_key = f"headway_{route_id}_{direction_id}_{time_window.total_seconds()}"
            self.headway_cache[cache_key] = {
                'analysis': analysis,
                'timestamp': datetime.utcnow()
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing headways: {str(e)}", exc_info=True)
            raise
    
    async def detect_anomalies(self, time_window: timedelta = timedelta(hours=1)) -> List[AnomalyDetection]:
        """Detect anomalies in transit data."""
        try:
            anomalies = []
            
            # Get recent data for analysis
            predictions = await transit_storage.get_recent_predictions(limit=500)
            alerts = await transit_storage.get_service_health_summary(hours=1)
            
            # Detect delay anomalies
            if predictions:
                delays = [p.get('delay', 0) for p in predictions if p.get('delay') is not None]
                if delays:
                    avg_delay = statistics.mean(delays)
                    delay_std = statistics.stdev(delays) if len(delays) > 1 else 0.0
                    
                    # Find extreme delays (>3 standard deviations)
                    threshold = avg_delay + (3 * delay_std)
                    extreme_delays = [d for d in delays if d > threshold]
                    
                    if extreme_delays:
                        affected_routes = list(set([
                            p.get('route_id') for p in predictions 
                            if p.get('delay', 0) > threshold
                        ]))
                        
                        anomalies.append(AnomalyDetection(
                            anomaly_type="extreme_delays",
                            severity="high" if len(extreme_delays) > 5 else "medium",
                            description=f"Detected {len(extreme_delays)} extreme delays above threshold",
                            affected_routes=affected_routes,
                            affected_stops=[],
                            confidence_score=0.85,
                            timestamp=datetime.utcnow()
                        ))
            
            # Detect service disruption patterns
            if alerts and alerts.get('total_alerts', 0) > 10:
                anomalies.append(AnomalyDetection(
                    anomaly_type="service_disruption",
                    severity="high",
                    description=f"High number of active alerts: {alerts.get('total_alerts', 0)}",
                    affected_routes=alerts.get('affected_routes', []),
                    affected_stops=alerts.get('affected_stops', []),
                    confidence_score=0.90,
                    timestamp=datetime.utcnow()
                ))
            
            # Cache results
            self.anomaly_cache['latest'] = {
                'anomalies': anomalies,
                'timestamp': datetime.utcnow()
            }
            
            return anomalies
            
        except Exception as e:
            logger.error(f"Error detecting anomalies: {str(e)}", exc_info=True)
            raise
    
    async def generate_service_summary(self, time_window: timedelta = timedelta(hours=1)) -> Dict[str, Any]:
        """Generate comprehensive service summary."""
        try:
            # Get performance metrics
            performance = await self.analyze_performance(time_window=time_window)
            
            # Get anomaly detection results
            anomalies = await self.detect_anomalies(time_window=time_window)
            
            # Get service health from storage
            service_health = await transit_storage.get_service_health_summary(
                hours=int(time_window.total_seconds() / 3600)
            )
            
            summary = {
                'timestamp': datetime.utcnow().isoformat(),
                'time_window_hours': time_window.total_seconds() / 3600,
                'performance': {
                    'on_time_percentage': performance.on_time_percentage,
                    'average_delay_minutes': performance.average_delay / 60,
                    'delayed_trips': performance.delayed_trips,
                    'total_trips': performance.total_trips
                },
                'service_health': service_health,
                'anomalies': [
                    {
                        'type': a.anomaly_type,
                        'severity': a.severity,
                        'description': a.description,
                        'confidence': a.confidence_score
                    }
                    for a in anomalies
                ],
                'overall_status': self._calculate_overall_status(performance, anomalies, service_health)
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating service summary: {str(e)}", exc_info=True)
            raise
    
    def _calculate_overall_status(self, performance: PerformanceMetrics, 
                                anomalies: List[AnomalyDetection],
                                service_health: Dict[str, Any]) -> str:
        """Calculate overall service status."""
        # Simple scoring system
        score = 100
        
        # Deduct points for delays
        if performance.on_time_percentage < 80:
            score -= 20
        elif performance.on_time_percentage < 90:
            score -= 10
        
        # Deduct points for anomalies
        high_severity_anomalies = len([a for a in anomalies if a.severity == 'high'])
        score -= high_severity_anomalies * 15
        
        # Deduct points for service disruptions
        if service_health.get('total_alerts', 0) > 5:
            score -= 10
        
        # Return status based on score
        if score >= 80:
            return "excellent"
        elif score >= 60:
            return "good"
        elif score >= 40:
            return "fair"
        else:
            return "poor"
    
    async def get_cached_metrics(self, metric_type: str, **kwargs) -> Optional[Any]:
        """Get cached metrics if they're still valid."""
        cache_key = f"{metric_type}_{'_'.join(str(v) for v in kwargs.values())}"
        
        if cache_key in getattr(self, f"{metric_type}_cache", {}):
            cache_entry = getattr(self, f"{metric_type}_cache")[cache_key]
            if datetime.utcnow() - cache_entry['timestamp'] < self.cache_ttl:
                return cache_entry.get('metrics') or cache_entry.get('analysis') or cache_entry.get('anomalies')
        
        return None
    
    def clear_cache(self, metric_type: Optional[str] = None):
        """Clear analytics cache."""
        if metric_type:
            cache_name = f"{metric_type}_cache"
            if hasattr(self, cache_name):
                getattr(self, cache_name).clear()
        else:
            self.performance_cache.clear()
            self.headway_cache.clear()
            self.anomaly_cache.clear()
    
    def process(self, data: Any) -> Any:
        """Process the input data and return processed result.
        
        This method is required by BaseProcessor but TransitAnalytics
        is primarily used for analysis rather than data processing.
        """
        # For analytics, we typically don't process individual data items
        # but rather analyze collections of data
        return data


# Global analytics instance
transit_analytics = TransitAnalytics()
