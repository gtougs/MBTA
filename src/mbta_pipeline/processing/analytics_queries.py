"""Pre-built SQL queries for MBTA transit analytics."""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta


class AnalyticsQueries:
    """Collection of SQL queries for transit analytics."""
    
    @staticmethod
    def get_performance_metrics(hours: int = 24, route_id: Optional[str] = None) -> str:
        """Get on-time performance metrics."""
        route_filter = f"AND p.route_id = '{route_id}'" if route_id else ""
        
        return f"""
        WITH performance_stats AS (
            SELECT 
                p.route_id,
                r.route_name,
                COUNT(*) as total_predictions,
                COUNT(CASE WHEN p.delay > 0 THEN 1 END) as delayed_predictions,
                COUNT(CASE WHEN p.delay > 300 THEN 1 END) as severely_delayed,
                AVG(CASE WHEN p.delay > 0 THEN p.delay ELSE 0 END) as avg_delay_seconds,
                STDDEV(CASE WHEN p.delay > 0 THEN p.delay ELSE 0 END) as delay_std_dev,
                AVG(p.delay) as overall_avg_delay
            FROM predictions p
            JOIN routes r ON p.route_id = r.id
            WHERE p.timestamp >= NOW() - INTERVAL '{hours} hours'
            {route_filter}
            GROUP BY p.route_id, r.route_name
        )
        SELECT 
            route_id,
            route_name,
            total_predictions,
            delayed_predictions,
            severely_delayed,
            ROUND(
                ((total_predictions - delayed_predictions)::numeric / total_predictions) * 100, 2
            ) as on_time_percentage,
            ROUND((avg_delay_seconds / 60.0)::numeric, 2) as avg_delay_minutes,
            ROUND((delay_std_dev / 60.0)::numeric, 2) as delay_std_dev_minutes,
            ROUND((overall_avg_delay / 60.0)::numeric, 2) as overall_avg_delay_minutes
        FROM performance_stats
        ORDER BY on_time_percentage DESC, total_predictions DESC;
        """
    
    @staticmethod
    def get_delay_trends(hours: int = 24, route_id: Optional[str] = None) -> str:
        """Get delay trends over time."""
        route_filter = f"AND p.route_id = '{route_id}'" if route_id else ""
        
        return f"""
        SELECT 
            DATE_TRUNC('hour', p.timestamp) as hour_bucket,
            COUNT(*) as total_predictions,
            COUNT(CASE WHEN p.delay > 0 THEN 1 END) as delayed_count,
            ROUND((AVG(p.delay) / 60.0)::numeric, 2) as avg_delay_minutes,
            ROUND((MAX(p.delay) / 60.0)::numeric, 2) as max_delay_minutes,
            ROUND(
                (COUNT(CASE WHEN p.delay > 0 THEN 1 END)::numeric / COUNT(*)) * 100, 2
            ) as delay_percentage
        FROM predictions p
        WHERE p.timestamp >= NOW() - INTERVAL '{hours} hours'
        {route_filter}
        GROUP BY hour_bucket
        ORDER BY hour_bucket DESC;
        """
    
    @staticmethod
    def get_route_comparison(hours: int = 24) -> str:
        """Compare performance across all routes."""
        return f"""
        SELECT 
            r.id as route_id,
            r.route_name,
            r.route_type,
            COUNT(p.id) as total_predictions,
            COUNT(CASE WHEN p.delay > 0 THEN 1 END) as delayed_predictions,
            ROUND(
                ((COUNT(p.id) - COUNT(CASE WHEN p.delay > 0 THEN 1 END))::numeric / COUNT(p.id)) * 100, 2
            ) as on_time_percentage,
            ROUND((AVG(CASE WHEN p.delay > 0 THEN p.delay ELSE 0 END) / 60.0)::numeric, 2) as avg_delay_minutes,
            ROUND((MAX(p.delay) / 60.0)::numeric, 2) as max_delay_minutes,
            COUNT(DISTINCT p.trip_id) as unique_trips,
            COUNT(DISTINCT p.stop_id) as unique_stops
        FROM routes r
        LEFT JOIN predictions p ON r.id = p.route_id 
            AND p.timestamp >= NOW() - INTERVAL '{hours} hours'
        GROUP BY r.id, r.route_name, r.route_type
        ORDER BY on_time_percentage DESC NULLS LAST;
        """
    
    @staticmethod
    def get_stop_performance(hours: int = 24, route_id: Optional[str] = None) -> str:
        """Get performance metrics by stop."""
        route_filter = f"AND p.route_id = '{route_id}'" if route_id else ""
        
        return f"""
        SELECT 
            s.id as stop_id,
            s.stop_name,
            s.stop_lat,
            s.stop_lon,
            COUNT(p.id) as total_predictions,
            COUNT(CASE WHEN p.delay > 0 THEN 1 END) as delayed_predictions,
            ROUND(
                ((COUNT(p.id) - COUNT(CASE WHEN p.delay > 0 THEN 1 END))::float / COUNT(p.id)) * 100, 2
            ) as on_time_percentage,
            ROUND(AVG(CASE WHEN p.delay > 0 THEN p.delay ELSE 0 END) / 60, 2) as avg_delay_minutes,
            ROUND(MAX(p.delay) / 60, 2) as max_delay_minutes
        FROM stops s
        JOIN predictions p ON s.id = p.stop_id
        WHERE p.timestamp >= NOW() - INTERVAL '{hours} hours'
        {route_filter}
        GROUP BY s.id, s.stop_name, s.stop_lat, s.stop_lon
        HAVING COUNT(p.id) >= 5  -- Only stops with sufficient data
        ORDER BY on_time_percentage DESC;
        """
    
    @staticmethod
    def get_vehicle_performance(hours: int = 24) -> str:
        """Get performance metrics by vehicle."""
        return f"""
        SELECT 
            v.id as vehicle_id,
            v.vehicle_label,
            COUNT(vp.id) as total_positions,
            COUNT(DISTINCT vp.trip_id) as unique_trips,
            COUNT(DISTINCT vp.route_id) as unique_routes,
            ROUND(AVG(vp.speed), 2) as avg_speed_mps,
            ROUND(MAX(vp.speed), 2) as max_speed_mps,
            COUNT(CASE WHEN vp.congestion_level > 0 THEN 1 END) as congestion_incidents,
            COUNT(CASE WHEN vp.occupancy_status > 0 THEN 1 END) as occupancy_incidents
        FROM vehicles v
        JOIN vehicle_positions vp ON v.id = vp.vehicle_id
        WHERE vp.timestamp >= NOW() - INTERVAL '{hours} hours'
        GROUP BY v.id, v.vehicle_label
        HAVING COUNT(vp.id) >= 10  -- Only vehicles with sufficient data
        ORDER BY total_positions DESC;
        """
    
    @staticmethod
    def get_service_alerts_summary(hours: int = 24) -> str:
        """Get summary of service alerts."""
        return f"""
        SELECT 
            alert_effect,
            alert_severity_level,
            COUNT(*) as alert_count,
            COUNT(DISTINCT affected_route_ids) as affected_routes,
            COUNT(DISTINCT affected_stop_ids) as affected_stops,
            MIN(timestamp) as first_alert,
            MAX(timestamp) as last_alert,
            ROUND(
                EXTRACT(EPOCH FROM (MAX(timestamp) - MIN(timestamp))) / 3600, 2
            ) as duration_hours
        FROM alerts
        WHERE timestamp >= NOW() - INTERVAL '{hours} hours'
        GROUP BY alert_effect, alert_severity_level
        ORDER BY alert_count DESC;
        """
    
    @staticmethod
    def get_headway_analysis(hours: int = 24, route_id: Optional[str] = None) -> str:
        """Analyze headways between consecutive vehicles."""
        route_filter = f"AND vp.route_id = '{route_id}'" if route_id else ""
        
        return f"""
        WITH vehicle_sequences AS (
            SELECT 
                vp.route_id,
                vp.direction_id,
                vp.vehicle_id,
                vp.timestamp,
                LAG(vp.timestamp) OVER (
                    PARTITION BY vp.route_id, vp.direction_id 
                    ORDER BY vp.timestamp
                ) as prev_timestamp
            FROM vehicle_positions vp
            WHERE vp.timestamp >= NOW() - INTERVAL '{hours} hours'
            {route_filter}
        ),
        headways AS (
            SELECT 
                route_id,
                direction_id,
                EXTRACT(EPOCH FROM (timestamp - prev_timestamp)) as headway_seconds
            FROM vehicle_sequences
            WHERE prev_timestamp IS NOT NULL
        )
        SELECT 
            h.route_id,
            r.route_name,
            h.direction_id,
            COUNT(*) as total_headways,
            ROUND(AVG(h.headway_seconds) / 60, 2) as avg_headway_minutes,
            ROUND(STDDEV(h.headway_seconds) / 60, 2) as headway_std_dev_minutes,
            ROUND(MIN(h.headway_seconds) / 60, 2) as min_headway_minutes,
            ROUND(MAX(h.headway_seconds) / 60, 2) as max_headway_minutes,
            COUNT(CASE WHEN h.headway_seconds < 180 THEN 1 END) as bunching_incidents,
            COUNT(CASE WHEN h.headway_seconds > 900 THEN 1 END) as gap_incidents
        FROM headways h
        JOIN routes r ON h.route_id = r.id
        GROUP BY h.route_id, r.route_name, h.direction_id
        HAVING COUNT(*) >= 5  -- Only routes with sufficient data
        ORDER BY avg_headway_minutes;
        """
    
    @staticmethod
    def get_peak_hour_analysis(hours: int = 24) -> str:
        """Analyze performance during peak vs off-peak hours."""
        return f"""
        WITH time_periods AS (
            SELECT 
                CASE 
                    WHEN EXTRACT(HOUR FROM p.timestamp) BETWEEN 7 AND 9 THEN 'Morning Peak (7-9 AM)'
                    WHEN EXTRACT(HOUR FROM p.timestamp) BETWEEN 16 AND 18 THEN 'Evening Peak (4-6 PM)'
                    WHEN EXTRACT(HOUR FROM p.timestamp) BETWEEN 10 AND 15 THEN 'Midday (10 AM-3 PM)'
                    WHEN EXTRACT(HOUR FROM p.timestamp) BETWEEN 19 AND 22 THEN 'Evening (7-10 PM)'
                    ELSE 'Late Night (11 PM-6 AM)'
                END as time_period,
                p.*
            FROM predictions p
            WHERE p.timestamp >= NOW() - INTERVAL '{hours} hours'
        )
        SELECT 
            time_period,
            COUNT(*) as total_predictions,
            COUNT(CASE WHEN delay > 0 THEN 1 END) as delayed_predictions,
            ROUND(
                ((COUNT(*) - COUNT(CASE WHEN delay > 0 THEN 1 END))::numeric / COUNT(*)) * 100, 2
            ) as on_time_percentage,
            ROUND((AVG(CASE WHEN delay > 0 THEN delay ELSE 0 END) / 60.0)::numeric, 2) as avg_delay_minutes,
            ROUND((MAX(delay) / 60.0)::numeric, 2) as max_delay_minutes
        FROM time_periods
        GROUP BY time_period
        ORDER BY 
            CASE time_period
                WHEN 'Morning Peak (7-9 AM)' THEN 1
                WHEN 'Evening Peak (4-6 PM)' THEN 2
                WHEN 'Midday (10 AM-3 PM)' THEN 3
                WHEN 'Evening (7-10 PM)' THEN 4
                ELSE 5
            END;
        """
    
    @staticmethod
    def get_anomaly_detection(hours: int = 24) -> str:
        """Detect anomalies in transit data."""
        return f"""
        WITH delay_stats AS (
            SELECT 
                route_id,
                AVG(delay) as avg_delay,
                STDDEV(delay) as delay_std_dev
            FROM predictions
            WHERE timestamp >= NOW() - INTERVAL '{hours} hours'
                AND delay IS NOT NULL
            GROUP BY route_id
        ),
        anomalies AS (
            SELECT 
                p.id,
                p.route_id,
                p.delay,
                p.timestamp,
                ds.avg_delay,
                ds.delay_std_dev,
                CASE 
                    WHEN p.delay > (ds.avg_delay + 3 * ds.delay_std_dev) THEN 'Extreme Delay'
                    WHEN p.delay > (ds.avg_delay + 2 * ds.delay_std_dev) THEN 'High Delay'
                    WHEN p.delay < (ds.avg_delay - 2 * ds.delay_std_dev) THEN 'Early Arrival'
                    ELSE 'Normal'
                END as anomaly_type
            FROM predictions p
            JOIN delay_stats ds ON p.route_id = ds.route_id
            WHERE p.timestamp >= NOW() - INTERVAL '{hours} hours'
                AND p.delay IS NOT NULL
                AND ds.delay_std_dev > 0
        )
        SELECT 
            anomaly_type,
            COUNT(*) as count,
            ROUND(AVG(delay) / 60, 2) as avg_delay_minutes,
            ROUND(MAX(delay) / 60, 2) as max_delay_minutes,
            COUNT(DISTINCT route_id) as affected_routes,
            MIN(timestamp) as first_occurrence,
            MAX(timestamp) as last_occurrence
        FROM anomalies
        WHERE anomaly_type != 'Normal'
        GROUP BY anomaly_type
        ORDER BY count DESC;
        """
    
    @staticmethod
    def get_realtime_dashboard_data() -> str:
        """Get data for real-time dashboard."""
        return """
        SELECT 
            'predictions' as data_type,
            COUNT(*) as count,
            COUNT(CASE WHEN delay > 0 THEN 1 END) as delayed_count,
            ROUND(AVG(CASE WHEN delay > 0 THEN delay ELSE 0 END) / 60, 2) as avg_delay_minutes
        FROM predictions
        WHERE timestamp >= NOW() - INTERVAL '1 hour'
        
        UNION ALL
        
        SELECT 
            'vehicles' as data_type,
            COUNT(DISTINCT vehicle_id) as count,
            COUNT(CASE WHEN congestion_level > 0 THEN 1 END) as congested_count,
            ROUND(AVG(speed), 2) as avg_speed_mps
        FROM vehicle_positions
        WHERE timestamp >= NOW() - INTERVAL '1 hour'
        
        UNION ALL
        
        SELECT 
            'alerts' as data_type,
            COUNT(*) as count,
            COUNT(CASE WHEN alert_severity_level = 'high' THEN 1 END) as high_severity_count,
            0 as avg_delay_minutes
        FROM alerts
        WHERE timestamp >= NOW() - INTERVAL '1 hour';
        """
    
    @staticmethod
    def get_geographic_performance(hours: int = 24) -> str:
        """Get performance metrics by geographic area."""
        return f"""
        SELECT 
            CASE 
                WHEN s.stop_lat BETWEEN 42.35 AND 42.37 AND s.stop_lon BETWEEN -71.07 AND -71.05 THEN 'Downtown Boston'
                WHEN s.stop_lat BETWEEN 42.33 AND 42.35 AND s.stop_lon BETWEEN -71.05 AND -71.03 THEN 'Cambridge'
                WHEN s.stop_lat BETWEEN 42.37 AND 42.39 AND s.stop_lon BETWEEN -71.05 AND -71.03 THEN 'Somerville'
                WHEN s.stop_lat BETWEEN 42.31 AND 42.33 AND s.stop_lon BETWEEN -71.03 AND -71.01 THEN 'Brookline'
                ELSE 'Other Areas'
            END as geographic_area,
            COUNT(p.id) as total_predictions,
            COUNT(CASE WHEN p.delay > 0 THEN 1 END) as delayed_predictions,
            ROUND(
                ((COUNT(p.id) - COUNT(CASE WHEN p.delay > 0 THEN 1 END))::float / COUNT(p.id)) * 100, 2
            ) as on_time_percentage,
            ROUND(AVG(CASE WHEN p.delay > 0 THEN p.delay ELSE 0 END) / 60, 2) as avg_delay_minutes,
            COUNT(DISTINCT p.route_id) as unique_routes,
            COUNT(DISTINCT p.stop_id) as unique_stops
        FROM predictions p
        JOIN stops s ON p.stop_id = s.id
        WHERE p.timestamp >= NOW() - INTERVAL '{hours} hours'
            AND s.stop_lat IS NOT NULL 
            AND s.stop_lon IS NOT NULL
        GROUP BY geographic_area
        ORDER BY total_predictions DESC;
        """
