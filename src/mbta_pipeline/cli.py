#!/usr/bin/env python3
"""Command-line interface for MBTA Data Pipeline."""

import argparse
import asyncio
import json
import sys
from datetime import datetime, timedelta
from typing import Optional

from mbta_pipeline.processing import DataAggregator
from mbta_pipeline.utils.logging import setup_logging, get_logger


class MBTAPipelineCLI:
    """CLI interface for MBTA pipeline operations."""
    
    def __init__(self):
        """Initialize the CLI."""
        self.logger = get_logger(__name__)
        self.aggregator = DataAggregator()
        
        # Setup logging
        setup_logging(level="INFO", enable_json=False)
    
    def parse_args(self):
        """Parse command line arguments."""
        parser = argparse.ArgumentParser(
            description="MBTA Data Pipeline CLI",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  # View current aggregation summary
  python -m mbta_pipeline.cli summary
  
  # View route-specific summary
  python -m mbta_pipeline.cli route-summary
  
  # View service health
  python -m mbta_pipeline.cli health
  
  # Export aggregations to JSON
  python -m mbta_pipeline.cli export --format json
  
  # View time-based summary for last hour
  python -m mbta_pipeline.cli time-summary --hours 1
            """
        )
        
        subparsers = parser.add_subparsers(dest="command", help="Available commands")
        
        # Summary command
        subparsers.add_parser("summary", help="Show comprehensive aggregation summary")
        
        # Route summary command
        subparsers.add_parser("route-summary", help="Show route-based summary")
        
        # Stop summary command
        subparsers.add_parser("stop-summary", help="Show stop-based summary")
        
        # Service health command
        subparsers.add_parser("health", help="Show service health summary")
        
        # Time-based summary command
        time_parser = subparsers.add_parser("time-summary", help="Show time-based summary")
        time_parser.add_argument(
            "--hours", "-H", 
            type=float, 
            default=1.0,
            help="Time window in hours (default: 1.0)"
        )
        
        # Export command
        export_parser = subparsers.add_parser("export", help="Export aggregations")
        export_parser.add_argument(
            "--format", "-f",
            choices=["json"],
            default="json",
            help="Export format (default: json)"
        )
        export_parser.add_argument(
            "--output", "-o",
            help="Output file path (default: stdout)"
        )
        
        # Clear command
        subparsers.add_parser("clear", help="Clear all aggregated data")
        
        # Stats command
        subparsers.add_parser("stats", help="Show processor statistics")
        
        return parser.parse_args()
    
    def display_summary(self):
        """Display comprehensive aggregation summary."""
        if not self.aggregator.aggregations:
            print("No data has been aggregated yet.")
            return
        
        stats = self.aggregator.get_summary_stats()
        
        print("=" * 60)
        print("MBTA DATA PIPELINE - AGGREGATION SUMMARY")
        print("=" * 60)
        print(f"Timestamp: {stats['timestamp']}")
        print(f"Total Records: {stats['total_records']}")
        print()
        
        # Data type breakdown
        print("DATA BY TYPE:")
        print("-" * 20)
        for data_type, type_stats in stats['by_type'].items():
            print(f"{data_type}: {type_stats['count']} records")
        print()
        
        # Service metrics
        service_metrics = stats['service_metrics']
        print("SERVICE METRICS:")
        print("-" * 20)
        print(f"Total Predictions: {service_metrics['total_predictions']}")
        print(f"Total Vehicles: {service_metrics['total_vehicles']}")
        print(f"Active Routes: {service_metrics['active_routes']}")
        print(f"Active Stops: {service_metrics['active_stops']}")
        print(f"Delayed Predictions: {service_metrics['delayed_predictions']}")
        print()
        
        # Performance metrics
        perf_metrics = stats['performance_metrics']
        print("PERFORMANCE METRICS:")
        print("-" * 20)
        print(f"Average Delay: {perf_metrics['avg_delay']:.1f} seconds")
        print(f"Maximum Delay: {perf_metrics['max_delay']} seconds")
        print(f"Minimum Delay: {perf_metrics['min_delay']} seconds")
        print(f"Total Delays: {perf_metrics['delay_count']}")
        print()
        
        # Alert summary
        alert_summary = stats['alert_summary']
        print("ALERT SUMMARY:")
        print("-" * 20)
        print(f"Total Alerts: {alert_summary['total_alerts']}")
        print(f"Active Alerts: {alert_summary['active_alerts']}")
        if alert_summary['by_severity']:
            print("By Severity:")
            for severity, count in alert_summary['by_severity'].items():
                print(f"  {severity}: {count}")
        print()
        
        # Geographic summary
        geo_summary = stats['geographic_summary']
        print("GEOGRAPHIC SUMMARY:")
        print("-" * 20)
        print(f"Total Stops: {geo_summary['total_stops']}")
        print(f"Total Vehicles: {geo_summary['total_vehicles']}")
        if geo_summary['by_region']:
            print("By Region:")
            for region, count in geo_summary['by_region'].items():
                print(f"  {region}: {count}")
    
    def display_route_summary(self):
        """Display route-based summary."""
        if not self.aggregator.aggregations:
            print("No data has been aggregated yet.")
            return
        
        route_summary = self.aggregator.get_route_summary()
        
        if not route_summary:
            print("No route data available.")
            return
        
        print("=" * 60)
        print("MBTA DATA PIPELINE - ROUTE SUMMARY")
        print("=" * 60)
        
        for route_id, stats in route_summary.items():
            print(f"\nRoute: {route_id}")
            print("-" * 30)
            print(f"  Predictions: {stats['predictions']}")
            print(f"  Vehicle Positions: {stats['vehicle_positions']}")
            print(f"  Alerts: {stats['alerts']}")
            print(f"  Average Delay: {stats['avg_delay']:.1f} seconds")
            print(f"  Max Delay: {stats['max_delay']} seconds")
            print(f"  Min Delay: {stats['min_delay']} seconds")
    
    def display_stop_summary(self):
        """Display stop-based summary."""
        if not self.aggregator.aggregations:
            print("No data has been aggregated yet.")
            return
        
        stop_summary = self.aggregator.get_stop_summary()
        
        if not stop_summary:
            print("No stop data available.")
            return
        
        print("=" * 60)
        print("MBTA DATA PIPELINE - STOP SUMMARY")
        print("=" * 60)
        
        for stop_id, stats in stop_summary.items():
            print(f"\nStop: {stop_id}")
            print("-" * 30)
            print(f"  Predictions: {stats['predictions']}")
            print(f"  Alerts: {stats['alerts']}")
            print(f"  Average Delay: {stats['avg_delay']:.1f} seconds")
            print(f"  Max Delay: {stats['max_delay']} seconds")
            print(f"  Min Delay: {stats['min_delay']} seconds")
    
    def display_service_health(self):
        """Display service health summary."""
        if not self.aggregator.aggregations:
            print("No data has been aggregated yet.")
            return
        
        health_summary = self.aggregator.get_service_health_summary()
        
        print("=" * 60)
        print("MBTA DATA PIPELINE - SERVICE HEALTH")
        print("=" * 60)
        print(f"Timestamp: {health_summary['timestamp']}")
        print(f"Service Status: {health_summary['service_status'].upper()}")
        print()
        
        print("OVERALL METRICS:")
        print("-" * 20)
        print(f"Total Predictions: {health_summary['total_predictions']}")
        print(f"Total Vehicles: {health_summary['total_vehicles']}")
        print(f"Total Alerts: {health_summary['total_alerts']}")
        print(f"Delay Percentage: {health_summary['delay_percentage']:.1f}%")
        print()
        
        print("DELAY BREAKDOWN:")
        print("-" * 20)
        breakdown = health_summary['delay_breakdown']
        print(f"Minor Delays (≤5 min): {breakdown['minor']}")
        print(f"Moderate Delays (5-15 min): {breakdown['moderate']}")
        print(f"Major Delays (>15 min): {breakdown['major']}")
    
    def display_time_summary(self, hours: float):
        """Display time-based summary."""
        if not self.aggregator.aggregations:
            print("No data has been aggregated yet.")
            return
        
        time_window = timedelta(hours=hours)
        time_summary = self.aggregator.get_time_based_summary(time_window)
        
        print("=" * 60)
        print("MBTA DATA PIPELINE - TIME-BASED SUMMARY")
        print("=" * 60)
        print(f"Time Window: {time_summary['time_window']}")
        print(f"Start Time: {time_summary['start_time']}")
        print(f"End Time: {time_summary['end_time']}")
        print()
        
        print("RECORD COUNTS:")
        print("-" * 20)
        print(f"Predictions: {time_summary['predictions']}")
        print(f"Vehicle Positions: {time_summary['vehicle_positions']}")
        print(f"Trip Updates: {time_summary['trip_updates']}")
        print(f"Alerts: {time_summary['alerts']}")
        print()
        
        print("DELAY STATISTICS:")
        print("-" * 20)
        print(f"Average Delay: {time_summary['avg_delay']:.1f} seconds")
        print(f"Maximum Delay: {time_summary['max_delay']} seconds")
        print(f"Minimum Delay: {time_summary['min_delay']} seconds")
        print(f"Total Delays: {len(time_summary['delays'])}")
    
    def export_data(self, format: str, output_file: Optional[str]):
        """Export aggregated data."""
        if not self.aggregator.aggregations:
            print("No data has been aggregated yet.")
            return
        
        try:
            if format == "json":
                data = self.aggregator.export_aggregations("json")
                
                if output_file:
                    with open(output_file, 'w') as f:
                        f.write(data)
                    print(f"Data exported to {output_file}")
                else:
                    print(data)
            else:
                print(f"Unsupported format: {format}")
                
        except Exception as e:
            print(f"Export failed: {e}")
    
    def clear_data(self):
        """Clear all aggregated data."""
        self.aggregator.clear_aggregations()
        print("All aggregated data has been cleared.")
    
    def display_stats(self):
        """Display processor statistics."""
        stats = self.aggregator.get_stats()
        
        print("=" * 60)
        print("MBTA DATA PIPELINE - PROCESSOR STATISTICS")
        print("=" * 60)
        print(f"Processor: {stats['processor']}")
        print(f"Processed Count: {stats['processed_count']}")
        print(f"Error Count: {stats['error_count']}")
        print(f"Success Rate: {stats['success_rate']:.2%}")
    
    def run(self):
        """Run the CLI."""
        args = self.parse_args()
        
        if not args.command:
            print("No command specified. Use --help for available commands.")
            return 1
        
        try:
            if args.command == "summary":
                self.display_summary()
            elif args.command == "route-summary":
                self.display_route_summary()
            elif args.command == "stop-summary":
                self.display_stop_summary()
            elif args.command == "health":
                self.display_service_health()
            elif args.command == "time-summary":
                self.display_time_summary(args.hours)
            elif args.command == "export":
                self.export_data(args.format, args.output)
            elif args.command == "clear":
                self.clear_data()
            elif args.command == "stats":
                self.display_stats()
            else:
                print(f"Unknown command: {args.command}")
                return 1
                
        except Exception as e:
            self.logger.error(f"CLI error: {e}", exc_info=True)
            print(f"Error: {e}")
            return 1
        
        return 0


def main():
    """Main entry point for CLI."""
    cli = MBTAPipelineCLI()
    sys.exit(cli.run())


if __name__ == "__main__":
    main()
