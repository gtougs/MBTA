"""Tests for the DataAggregator class."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock

from src.mbta_pipeline.processing.aggregator import DataAggregator
from src.mbta_pipeline.models.transit import (
    Prediction, VehiclePosition, TripUpdate, Alert, Stop, Route, Trip
)


class TestDataAggregator:
    """Test cases for DataAggregator."""
    
    @pytest.fixture
    def aggregator(self):
        """Create a fresh aggregator instance for each test."""
        return DataAggregator()
    
    @pytest.fixture
    def sample_prediction(self):
        """Create a sample prediction for testing."""
        return Prediction(
            prediction_id="pred_1",
            trip_id="trip_1",
            stop_id="stop_1",
            route_id="Red",
            arrival_time=datetime.now() + timedelta(minutes=5),
            delay=120,
            source="mbta_v3_api"
        )
    
    @pytest.fixture
    def sample_vehicle_position(self):
        """Create a sample vehicle position for testing."""
        return VehiclePosition(
            vehicle_id="vehicle_1",
            trip_id="trip_1",
            route_id="Red",
            latitude=42.3564,
            longitude=-71.0624,
            timestamp=datetime.now(),
            source="mbta_gtfs_rt"
        )
    
    @pytest.fixture
    def sample_alert(self):
        """Create a sample alert for testing."""
        return Alert(
            alert_id="alert_1",
            alert_header_text="Service Delay",
            alert_description_text="Red Line experiencing delays",
            affected_routes=["Red"],
            affected_stops=["stop_1", "stop_2"],
            alert_severity_level="moderate",
            source="mbta_gtfs_rt"
        )
    
    def test_initialization(self, aggregator):
        """Test aggregator initialization."""
        assert aggregator.name == "DataAggregator"
        assert aggregator.aggregations == {}
        assert aggregator.summary_stats == {}
    
    def test_process_data(self, aggregator, sample_prediction):
        """Test processing individual data items."""
        result = aggregator.process(sample_prediction)
        assert result == sample_prediction
        assert "Prediction" in aggregator.aggregations
        assert len(aggregator.aggregations["Prediction"]) == 1
        assert aggregator.aggregations["Prediction"][0] == sample_prediction
    
    def test_process_batch(self, aggregator, sample_prediction, sample_vehicle_position):
        """Test processing batch of data items."""
        data_list = [sample_prediction, sample_vehicle_position]
        results = aggregator.process_batch(data_list)
        
        assert len(results) == 2
        assert "Prediction" in aggregator.aggregations
        assert "VehiclePosition" in aggregator.aggregations
        assert len(aggregator.aggregations["Prediction"]) == 1
        assert len(aggregator.aggregations["VehiclePosition"]) == 1
    
    def test_get_aggregations_by_type(self, aggregator, sample_prediction):
        """Test getting aggregations by specific type."""
        aggregator.process(sample_prediction)
        
        pred_aggs = aggregator.get_aggregations("Prediction")
        assert "Prediction" in pred_aggs
        assert len(pred_aggs["Prediction"]) == 1
        
        # Test non-existent type
        empty_aggs = aggregator.get_aggregations("NonExistent")
        assert "NonExistent" in empty_aggs
        assert empty_aggs["NonExistent"] == []
    
    def test_get_aggregations_all(self, aggregator, sample_prediction, sample_vehicle_position):
        """Test getting all aggregations."""
        aggregator.process(sample_prediction)
        aggregator.process(sample_vehicle_position)
        
        all_aggs = aggregator.get_aggregations()
        assert "Prediction" in all_aggs
        assert "VehiclePosition" in all_aggs
        assert len(all_aggs["Prediction"]) == 1
        assert len(all_aggs["VehiclePosition"]) == 1
    
    def test_get_summary_stats(self, aggregator, sample_prediction, sample_vehicle_position):
        """Test getting comprehensive summary statistics."""
        aggregator.process(sample_prediction)
        aggregator.process(sample_vehicle_position)
        
        stats = aggregator.get_summary_stats()
        
        assert "timestamp" in stats
        assert "total_records" in stats
        assert "by_type" in stats
        assert "service_metrics" in stats
        assert "performance_metrics" in stats
        assert "alert_summary" in stats
        assert "geographic_summary" in stats
        
        assert stats["total_records"] == 2
        assert "Prediction" in stats["by_type"]
        assert "VehiclePosition" in stats["by_type"]
    
    def test_get_route_summary(self, aggregator, sample_prediction, sample_vehicle_position, sample_alert):
        """Test getting route-based summary."""
        aggregator.process(sample_prediction)
        aggregator.process(sample_vehicle_position)
        aggregator.process(sample_alert)
        
        route_summary = aggregator.get_route_summary()
        
        assert "Red" in route_summary
        red_stats = route_summary["Red"]
        
        assert red_stats["predictions"] == 1
        assert red_stats["vehicle_positions"] == 1
        assert red_stats["alerts"] == 1
        assert red_stats["avg_delay"] == 120
        assert red_stats["max_delay"] == 120
        assert red_stats["min_delay"] == 120
    
    def test_get_stop_summary(self, aggregator, sample_prediction, sample_alert):
        """Test getting stop-based summary."""
        aggregator.process(sample_prediction)
        aggregator.process(sample_alert)
        
        stop_summary = aggregator.get_stop_summary()
        
        assert "stop_1" in stop_summary
        stop_1_stats = stop_summary["stop_1"]
        
        assert stop_1_stats["predictions"] == 1
        assert stop_1_stats["alerts"] == 1
        assert stop_1_stats["avg_delay"] == 120
    
    def test_get_time_based_summary(self, aggregator, sample_prediction, sample_vehicle_position):
        """Test getting time-based summary."""
        aggregator.process(sample_prediction)
        aggregator.process(sample_vehicle_position)
        
        time_summary = aggregator.get_time_based_summary(timedelta(hours=1))
        
        assert "time_window" in time_summary
        assert "start_time" in time_summary
        assert "end_time" in time_summary
        assert time_summary["predictions"] == 1
        assert time_summary["vehicle_positions"] == 1
        assert time_summary["avg_delay"] == 120
    
    def test_get_service_health_summary(self, aggregator, sample_prediction, sample_alert):
        """Test getting service health summary."""
        aggregator.process(sample_prediction)
        aggregator.process(sample_alert)
        
        health_summary = aggregator.get_service_health_summary()
        
        assert "timestamp" in health_summary
        assert "total_predictions" in health_summary
        assert "total_alerts" in health_summary
        assert "delay_percentage" in health_summary
        assert "delay_breakdown" in health_summary
        assert "service_status" in health_summary
        
        assert health_summary["total_predictions"] == 1
        assert health_summary["total_alerts"] == 1
        assert health_summary["delay_percentage"] == 100.0
        assert health_summary["delay_breakdown"]["minor"] == 0
        assert health_summary["delay_breakdown"]["moderate"] == 1
        assert health_summary["delay_breakdown"]["major"] == 0
    
    def test_context_manager(self, aggregator):
        """Test aggregator as context manager."""
        with aggregator as agg:
            assert agg.start_time is not None
            assert agg.name == "DataAggregator"
        
        # After context exit, stats should be available
        stats = aggregator.get_stats()
        assert stats["processor"] == "DataAggregator"
        assert stats["processed_count"] == 0
        assert stats["error_count"] == 0
    
    def test_clear_aggregations(self, aggregator, sample_prediction):
        """Test clearing all aggregations."""
        aggregator.process(sample_prediction)
        assert len(aggregator.aggregations) > 0
        
        aggregator.clear_aggregations()
        assert len(aggregator.aggregations) == 0
        assert len(aggregator.summary_stats) == 0
    
    def test_export_aggregations_json(self, aggregator, sample_prediction):
        """Test exporting aggregations to JSON."""
        aggregator.process(sample_prediction)
        
        json_export = aggregator.export_aggregations("json")
        assert isinstance(json_export, str)
        assert "Prediction" in json_export
        assert "pred_1" in json_export
    
    def test_export_unsupported_format(self, aggregator):
        """Test exporting with unsupported format raises error."""
        with pytest.raises(ValueError, match="Unsupported export format"):
            aggregator.export_aggregations("xml")
    
    def test_alert_active_status(self, aggregator):
        """Test alert active status checking."""
        # Active alert (no time constraints)
        active_alert = Alert(
            alert_id="active_1",
            alert_header_text="Active Alert",
            source="mbta_gtfs_rt"
        )
        
        # Future alert
        future_alert = Alert(
            alert_id="future_1",
            alert_header_text="Future Alert",
            effective_start_date=datetime.now() + timedelta(hours=1),
            source="mbta_gtfs_rt"
        )
        
        # Expired alert
        expired_alert = Alert(
            alert_id="expired_1",
            alert_header_text="Expired Alert",
            effective_end_date=datetime.now() - timedelta(hours=1),
            source="mbta_gtfs_rt"
        )
        
        aggregator.process(active_alert)
        aggregator.process(future_alert)
        aggregator.process(expired_alert)
        
        alert_summary = aggregator._get_alert_summary()
        assert alert_summary["total_alerts"] == 3
        assert alert_summary["active_alerts"] == 1
    
    def test_performance_metrics_with_delays(self, aggregator):
        """Test performance metrics calculation with delays."""
        # Create predictions with various delays
        delays = [0, 60, 300, 900, 1800]  # 0s, 1min, 5min, 15min, 30min
        
        for i, delay in enumerate(delays):
            pred = Prediction(
                prediction_id=f"pred_{i}",
                trip_id=f"trip_{i}",
                stop_id=f"stop_{i}",
                route_id="Red",
                delay=delay,
                source="mbta_v3_api"
            )
            aggregator.process(pred)
        
        perf_metrics = aggregator._get_performance_metrics()
        
        assert perf_metrics["avg_delay"] == 532.0  # (0+60+300+900+1800)/5
        assert perf_metrics["max_delay"] == 1800
        assert perf_metrics["min_delay"] == 0
        assert perf_metrics["delay_count"] == 5
    
    def test_performance_metrics_no_delays(self, aggregator):
        """Test performance metrics when no delays exist."""
        pred = Prediction(
            prediction_id="pred_1",
            trip_id="trip_1",
            stop_id="stop_1",
            route_id="Red",
            delay=None,
            source="mbta_v3_api"
        )
        aggregator.process(pred)
        
        perf_metrics = aggregator._get_performance_metrics()
        
        assert perf_metrics["avg_delay"] == 0
        assert perf_metrics["max_delay"] == 0
        assert perf_metrics["min_delay"] == 0
        assert perf_metrics["delay_count"] == 0
    
    def test_service_status_calculation(self, aggregator):
        """Test service status calculation based on delays and alerts."""
        # Test excellent status
        status = aggregator._get_overall_service_status(2.0, 1)
        assert status == "excellent"
        
        # Test good status
        status = aggregator._get_overall_service_status(7.0, 3)
        assert status == "good"
        
        # Test fair status
        status = aggregator._get_overall_service_status(15.0, 7)
        assert status == "fair"
        
        # Test poor status
        status = aggregator._get_overall_service_status(25.0, 12)
        assert status == "poor"
    
    def test_error_handling_in_batch_processing(self, aggregator):
        """Test error handling during batch processing."""
        # Create a mock object that will raise an exception
        bad_data = Mock()
        bad_data.side_effect = Exception("Test error")
        
        good_data = sample_prediction = Prediction(
            prediction_id="pred_1",
            trip_id="trip_1",
            stop_id="stop_1",
            route_id="Red",
            source="mbta_v3_api"
        )
        
        data_list = [good_data, bad_data]
        results = aggregator.process_batch(data_list)
        
        # Should process good data and handle bad data gracefully
        assert len(results) == 1
        assert aggregator.error_count == 1
        assert aggregator.processed_count == 1


if __name__ == "__main__":
    pytest.main([__file__])
