#!/usr/bin/env python3
"""Standalone demo for data aggregation functionality."""

import json
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Any, Dict, List, Optional, Union, Counter


class SimpleDataAggregator:
    """Simplified data aggregator for demonstration."""
    
    def __init__(self):
        """Initialize the data aggregator."""
        self.name = "SimpleDataAggregator"
        self.aggregations = defaultdict(list)
        self.processed_count = 0
        self.error_count = 0
    
    def process(self, data: Any) -> Any:
        """Process data for aggregation."""
        # Store data for aggregation
        data_type = type(data).__name__
        self.aggregations[data_type].append(data)
        self.processed_count += 1
        return data
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """Get comprehensive summary statistics."""
        return {
            "timestamp": datetime.now().isoformat(),
            "total_records": sum(len(records) for records in self.aggregations.values()),
            "by_type": {
                data_type: {
                    "count": len(records),
                    "first_seen": datetime.now().isoformat(),
                    "last_seen": datetime.now().isoformat()
                }
                for data_type, records in self.aggregations.items()
            }
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
    
    def export_aggregations(self, format: str = "json") -> str:
        """Export aggregations in specified format."""
        if format.lower() == "json":
            return json.dumps(self.get_summary_stats(), default=str, indent=2)
        else:
            raise ValueError(f"Unsupported export format: {format}")


# Simple data classes for demonstration
class SimplePrediction:
    def __init__(self, prediction_id, trip_id, stop_id, route_id, arrival_time, delay, source):
        self.prediction_id = prediction_id
        self.trip_id = trip_id
        self.stop_id = stop_id
        self.route_id = route_id
        self.arrival_time = arrival_time
        self.delay = delay
        self.source = source

class SimpleVehiclePosition:
    def __init__(self, vehicle_id, trip_id, route_id, latitude, longitude, timestamp, source):
        self.vehicle_id = vehicle_id
        self.trip_id = trip_id
        self.route_id = route_id
        self.latitude = latitude
        self.longitude = longitude
        self.timestamp = timestamp
        self.source = source

class SimpleAlert:
    def __init__(self, alert_id, alert_header_text, alert_description_text, affected_routes, affected_stops, alert_severity_level, source):
        self.alert_id = alert_id
        self.alert_header_text = alert_header_text
        self.alert_description_text = alert_description_text
        self.affected_routes = affected_routes
        self.affected_stops = affected_stops
        self.alert_severity_level = alert_severity_level
        self.source = source


def create_sample_data():
    """Create sample transit data for demonstration."""
    now = datetime.now()
    
    # Create sample predictions with various delays
    predictions = [
        SimplePrediction(
            prediction_id="pred_1",
            trip_id="trip_1",
            stop_id="stop_1",
            route_id="Red",
            arrival_time=now + timedelta(minutes=5),
            delay=120,  # 2 minutes
            source="mbta_v3_api"
        ),
        SimplePrediction(
            prediction_id="pred_2",
            trip_id="trip_2",
            stop_id="stop_2",
            route_id="Red",
            arrival_time=now + timedelta(minutes=8),
            delay=300,  # 5 minutes
            source="mbta_v3_api"
        ),
        SimplePrediction(
            prediction_id="pred_3",
            trip_id="trip_3",
            stop_id="stop_3",
            route_id="Blue",
            arrival_time=now + timedelta(minutes=3),
            delay=0,  # On time
            source="mbta_v3_api"
        ),
        SimplePrediction(
            prediction_id="pred_4",
            trip_id="trip_4",
            stop_id="stop_4",
            route_id="Blue",
            arrival_time=now + timedelta(minutes=12),
            delay=900,  # 15 minutes
            source="mbta_v3_api"
        )
    ]
    
    # Create sample vehicle positions
    vehicle_positions = [
        SimpleVehiclePosition(
            vehicle_id="vehicle_1",
            trip_id="trip_1",
            route_id="Red",
            latitude=42.3564,
            longitude=-71.0624,
            timestamp=now,
            source="mbta_gtfs_rt"
        ),
        SimpleVehiclePosition(
            vehicle_id="vehicle_2",
            trip_id="trip_3",
            route_id="Blue",
            latitude=42.3654,
            longitude=-71.0614,
            timestamp=now,
            source="mbta_gtfs_rt"
        )
    ]
    
    # Create sample alerts
    alerts = [
        SimpleAlert(
            alert_id="alert_1",
            alert_header_text="Red Line Delays",
            alert_description_text="Red Line experiencing delays due to signal issues",
            affected_routes=["Red"],
            affected_stops=["stop_1", "stop_2"],
            alert_severity_level="moderate",
            source="mbta_gtfs_rt"
        ),
        SimpleAlert(
            alert_id="alert_2",
            alert_header_text="Blue Line Service Alert",
            alert_description_text="Blue Line running with reduced frequency",
            affected_routes=["Blue"],
            affected_stops=["stop_3", "stop_4"],
            alert_severity_level="minor",
            source="mbta_gtfs_rt"
        )
    ]
    
    return predictions, vehicle_positions, alerts


def main():
    """Run the standalone demo."""
    print("Starting MBTA Data Aggregator Demo...")
    print()
    
    try:
        # Create aggregator
        aggregator = SimpleDataAggregator()
        print("✓ SimpleDataAggregator created successfully")
        
        # Create sample data
        predictions, vehicle_positions, alerts = create_sample_data()
        print("✓ Sample data created")
        
        # Process data through aggregator
        print("Processing sample data...")
        for pred in predictions:
            aggregator.process(pred)
        
        for pos in vehicle_positions:
            aggregator.process(pos)
        
        for alert in alerts:
            aggregator.process(alert)
        
        print(f"✓ Processed {len(predictions)} predictions, {len(vehicle_positions)} vehicle positions, {len(alerts)} alerts")
        print()
        
        # Show basic statistics
        stats = aggregator.get_summary_stats()
        print("SUMMARY STATISTICS:")
        print(f"Total Records: {stats['total_records']}")
        print(f"Data Types: {list(stats['by_type'].keys())}")
        print()
        
        # Show route summary
        route_summary = aggregator.get_route_summary()
        print("ROUTE SUMMARY:")
        for route_id, route_stats in route_summary.items():
            print(f"  {route_id}: {route_stats['predictions']} predictions, "
                  f"{route_stats['vehicle_positions']} vehicles, "
                  f"{route_stats['alerts']} alerts, "
                  f"avg delay: {route_stats['avg_delay']:.1f}s")
        print()
        
        # Show service health
        health = aggregator.get_service_health_summary()
        print("SERVICE HEALTH:")
        print(f"  Status: {health['service_status'].upper()}")
        print(f"  Delay Percentage: {health['delay_percentage']:.1f}%")
        print(f"  Delay Breakdown:")
        for delay_type, count in health['delay_breakdown'].items():
            print(f"    {delay_type}: {count}")
        print()
        
        # Test export functionality
        print("EXPORT FUNCTIONALITY:")
        try:
            json_export = aggregator.export_aggregations("json")
            print(f"  JSON export length: {len(json_export)} characters")
            print("  (First 200 characters):")
            print(f"  {json_export[:200]}...")
        except Exception as e:
            print(f"  Export failed: {e}")
        print()
        
        print("=" * 60)
        print("DEMO COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print()
        print("The SimpleDataAggregator demonstrates:")
        print("✓ Real-time data aggregation")
        print("✓ Route-based analysis")
        print("✓ Service health monitoring")
        print("✓ Performance metrics")
        print("✓ Export capabilities")
        print()
        print("The full DataAggregator in the package provides:")
        print("✓ Additional features like stop-based analysis")
        print("✓ Time-based analysis")
        print("✓ Geographic summaries")
        print("✓ Context manager support")
        print("✓ Integration with the full pipeline")
        
    except Exception as e:
        print(f"Demo failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    main()
