#!/usr/bin/env python3
"""CLI interface for MBTA Data Pipeline."""

import asyncio
import click
import sys
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from mbta_pipeline.storage.init_database import initialize_database, verify_database, reset_database
from mbta_pipeline.processing.analytics import transit_analytics
from mbta_pipeline.processing.analytics_queries import AnalyticsQueries
from mbta_pipeline.storage.database import DatabaseManager
from mbta_pipeline.utils.logging import setup_logging, get_logger


@click.group()
@click.option('--log-level', default='INFO', help='Logging level')
def cli(log_level):
    """MBTA Data Pipeline CLI."""
    setup_logging(level=log_level)
    pass


@cli.command()
@click.option('--force', is_flag=True, help='Force recreation of tables')
def init_db(force):
    """Initialize the database and create tables."""
    async def _init_db():
        if force:
            click.echo("Resetting database...")
            success = await reset_database()
        else:
            click.echo("Initializing database...")
            success = await initialize_database()
        
        if success:
            click.echo("✅ Database initialized successfully!")
            
            # Verify database
            status = await verify_database()
            click.echo(f"Database status: {status['status']}")
            click.echo(f"Tables: {status['table_counts']}")
            click.echo(f"Size: {status['database_size']}")
        else:
            click.echo("❌ Database initialization failed!")
            sys.exit(1)
    
    asyncio.run(_init_db())


@cli.command()
def verify_db():
    """Verify database setup and connection."""
    async def _verify_db():
        status = await verify_database()
        
        click.echo("Database Status:")
        click.echo(f"  Status: {status['status']}")
        click.echo(f"  Timestamp: {status['timestamp']}")
        
        if status['status'] == 'healthy':
            click.echo("  ✅ Database is healthy!")
            click.echo(f"  Table counts: {status['table_counts']}")
            click.echo(f"  Database size: {status['database_size']}")
            click.echo(f"  Connection pool: {status['connection_pool']}")
        else:
            click.echo(f"  ❌ Database error: {status.get('error', 'Unknown error')}")
            sys.exit(1)
    
    asyncio.run(_verify_db())


@cli.command()
@click.option('--hours', default=24, help='Hours to analyze')
@click.option('--route', help='Specific route ID to analyze')
def performance(hours, route):
    """Analyze transit performance metrics."""
    async def _performance():
        click.echo(f"Analyzing performance for the last {hours} hours...")
        
        try:
            metrics = await transit_analytics.analyze_performance(
                route_id=route, 
                time_window=timedelta(hours=hours)
            )
            
            click.echo("\n📊 Performance Metrics:")
            click.echo(f"  On-time percentage: {metrics.on_time_percentage:.1f}%")
            click.echo(f"  Average delay: {metrics.average_delay / 60:.1f} minutes")
            click.echo(f"  Total trips: {metrics.total_trips}")
            click.echo(f"  Delayed trips: {metrics.delayed_trips}")
            click.echo(f"  Severely delayed: {metrics.severely_delayed_trips}")
            
        except Exception as e:
            click.echo(f"❌ Error analyzing performance: {str(e)}")
            sys.exit(1)
    
    from datetime import timedelta
    asyncio.run(_performance())


@cli.command()
@click.option('--hours', default=24, help='Hours to analyze')
def anomalies(hours):
    """Detect anomalies in transit data."""
    async def _anomalies():
        click.echo(f"Detecting anomalies for the last {hours} hours...")
        
        try:
            anomalies = await transit_analytics.detect_anomalies(
                time_window=timedelta(hours=hours)
            )
            
            if not anomalies:
                click.echo("✅ No anomalies detected")
                return
            
            click.echo(f"\n🚨 Detected {len(anomalies)} anomalies:")
            for i, anomaly in enumerate(anomalies, 1):
                click.echo(f"  {i}. {anomaly.anomaly_type} ({anomaly.severity})")
                click.echo(f"     Description: {anomaly.description}")
                click.echo(f"     Confidence: {anomaly.confidence_score:.2f}")
                click.echo(f"     Affected routes: {', '.join(anomaly.affected_routes)}")
                click.echo()
                
        except Exception as e:
            click.echo(f"❌ Error detecting anomalies: {str(e)}")
            sys.exit(1)
    
    from datetime import timedelta
    asyncio.run(_anomalies())


@cli.command()
@click.option('--hours', default=24, help='Hours to analyze')
def summary(hours):
    """Generate comprehensive service summary."""
    async def _summary():
        click.echo(f"Generating service summary for the last {hours} hours...")
        
        try:
            summary = await transit_analytics.generate_service_summary(
                time_window=timedelta(hours=hours)
            )
            
            click.echo("\n📋 Service Summary:")
            click.echo(f"  Overall status: {summary['overall_status'].upper()}")
            click.echo(f"  Time window: {summary['time_window_hours']:.1f} hours")
            
            click.echo("\n📊 Performance:")
            perf = summary['performance']
            click.echo(f"  On-time percentage: {perf['on_time_percentage']:.1f}%")
            click.echo(f"  Average delay: {perf['average_delay_minutes']:.1f} minutes")
            click.echo(f"  Total trips: {perf['total_trips']}")
            click.echo(f"  Delayed trips: {perf['delayed_trips']}")
            
            click.echo(f"\n🚨 Anomalies: {len(summary['anomalies'])}")
            for anomaly in summary['anomalies']:
                click.echo(f"  - {anomaly['type']} ({anomaly['severity']})")
            
        except Exception as e:
            click.echo(f"❌ Error generating summary: {str(e)}")
            sys.exit(1)
    
    from datetime import timedelta
    asyncio.run(_summary())


@cli.command()
@click.option('--query', required=True, help='Query name to run')
@click.option('--hours', default=24, help='Hours to analyze')
@click.option('--route', help='Specific route ID')
def query(query, hours, route):
    """Run pre-built analytics queries."""
    async def _query():
        click.echo(f"Running query: {query}")
        
        try:
            db_manager = DatabaseManager()
            session = db_manager.get_session()
            
            try:
                # Get the SQL query
                if query == 'performance':
                    sql = AnalyticsQueries.get_performance_metrics(hours, route)
                elif query == 'delays':
                    sql = AnalyticsQueries.get_delay_trends(hours, route)
                elif query == 'routes':
                    sql = AnalyticsQueries.get_route_comparison(hours)
                elif query == 'stops':
                    sql = AnalyticsQueries.get_stop_performance(hours, route)
                elif query == 'vehicles':
                    sql = AnalyticsQueries.get_vehicle_performance(hours)
                elif query == 'alerts':
                    sql = AnalyticsQueries.get_service_alerts_summary(hours)
                elif query == 'headways':
                    sql = AnalyticsQueries.get_headway_analysis(hours, route)
                elif query == 'peak':
                    sql = AnalyticsQueries.get_peak_hour_analysis(hours)
                elif query == 'anomalies':
                    sql = AnalyticsQueries.get_anomaly_detection(hours)
                elif query == 'realtime':
                    sql = AnalyticsQueries.get_realtime_dashboard_data()
                elif query == 'geographic':
                    sql = AnalyticsQueries.get_geographic_performance(hours)
                else:
                    click.echo(f"❌ Unknown query: {query}")
                    click.echo("Available queries: performance, delays, routes, stops, vehicles, alerts, headways, peak, anomalies, realtime, geographic")
                    return
                
                # Execute query
                result = session.execute(sql)
                rows = result.fetchall()
                
                if not rows:
                    click.echo("No data returned")
                    return
                
                # Display results
                click.echo(f"\n📊 Query Results ({len(rows)} rows):")
                
                # Get column names
                columns = result.keys()
                click.echo("  " + " | ".join(str(col) for col in columns))
                click.echo("  " + "-" * (len(columns) * 10))
                
                for row in rows[:20]:  # Limit to first 20 rows
                    click.echo("  " + " | ".join(str(val) for val in row))
                
                if len(rows) > 20:
                    click.echo(f"  ... and {len(rows) - 20} more rows")
                
            finally:
                session.close()
                
        except Exception as e:
            click.echo(f"❌ Query error: {str(e)}")
            sys.exit(1)
    
    asyncio.run(_query())


@cli.command()
def run():
    """Run the main MBTA pipeline."""
    click.echo("Starting MBTA Data Pipeline...")
    
    try:
        from mbta_pipeline.main import main
        asyncio.run(main())
    except KeyboardInterrupt:
        click.echo("\nPipeline stopped by user")
    except Exception as e:
        click.echo(f"❌ Pipeline error: {str(e)}")
        sys.exit(1)


@cli.command()
def list_queries():
    """List available analytics queries."""
    click.echo("📊 Available Analytics Queries:")
    click.echo("  performance  - On-time performance metrics")
    click.echo("  delays       - Delay trends over time")
    click.echo("  routes       - Performance comparison across routes")
    click.echo("  stops        - Performance metrics by stop")
    click.echo("  vehicles     - Vehicle performance metrics")
    click.echo("  alerts       - Service alerts summary")
    click.echo("  headways     - Headway analysis between vehicles")
    click.echo("  peak         - Peak vs off-peak performance")
    click.echo("  anomalies    - Anomaly detection results")
    click.echo("  realtime     - Real-time dashboard data")
    click.echo("  geographic   - Performance by geographic area")
    
    click.echo("\n💡 Usage examples:")
    click.echo("  python -m src.cli query performance --hours 48")
    click.echo("  python -m src.cli query routes --hours 24")
    click.echo("  python -m src.cli query delays --route Red --hours 12")


if __name__ == "__main__":
    cli()
