#!/usr/bin/env python3
"""Main entry point for MBTA Data Pipeline."""

import asyncio
import signal
import sys
from typing import List, Dict, Any
from datetime import datetime

from src.mbta_pipeline.config.settings import settings
from src.mbta_pipeline.ingestion import V3RestIngestor, GTFSRTIngestor
from src.mbta_pipeline.utils.logging import setup_logging, get_logger
from src.mbta_pipeline.kafka import KafkaProducerWrapper
from src.mbta_pipeline.processing.aggregator import DataAggregator
from src.mbta_pipeline.processing.analytics import transit_analytics
from src.mbta_pipeline.storage.init_database import initialize_database, verify_database


class MBTAPipeline:
    """Main pipeline orchestrator for MBTA data ingestion."""
    
    def __init__(self):
        """Initialize the pipeline."""
        self.logger = get_logger(__name__)
        self.ingestors: List[Any] = []
        self.running = False
        self.tasks: List[asyncio.Task] = []
        self.kafka_producer: KafkaProducerWrapper | None = None
        self.aggregator = DataAggregator()
        self.analytics_enabled = True
        
        # Setup logging
        setup_logging(
            level=settings.log_level,
            enable_json=settings.environment == "production"
        )
        
        self.logger.info("MBTA Data Pipeline initializing", version="0.1.0")
    
    async def initialize_pipeline(self) -> None:
        """Initialize the entire pipeline including database and ingestors."""
        try:
            # Initialize database first
            self.logger.info("Initializing database...")
            db_success = await initialize_database()
            if not db_success:
                raise RuntimeError("Database initialization failed")
            
            # Verify database setup
            db_status = await verify_database()
            self.logger.info("Database status", status=db_status)
            
            # Initialize ingestors
            await self.initialize_ingestors()
            
            # Initialize analytics
            if self.analytics_enabled:
                self.logger.info("Analytics layer initialized")
            
            self.logger.info("Pipeline initialization completed successfully")
            
        except Exception as e:
            self.logger.error(f"Pipeline initialization failed: {str(e)}", exc_info=True)
            raise
    
    async def initialize_ingestors(self) -> None:
        """Initialize all data ingestors."""
        try:
            # Initialize V3 REST ingestor with session
            v3_ingestor = V3RestIngestor()
            await v3_ingestor.initialize_session()  # Initialize the HTTP session
            self.ingestors.append(v3_ingestor)
            self.logger.info("V3 REST ingestor initialized")
            
            # Initialize GTFS-RT ingestor with session
            gtfs_ingestor = GTFSRTIngestor()
            await gtfs_ingestor.initialize_session()  # Initialize the HTTP session
            self.ingestors.append(gtfs_ingestor)
            self.logger.info("GTFS-RT ingestor initialized")

            # Initialize Kafka producer
            self.kafka_producer = KafkaProducerWrapper()
            self.logger.info("Kafka producer initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize ingestors: {str(e)}", exc_info=True)
            raise
    
    async def start_ingestors(self) -> None:
        """Start all ingestors in continuous mode."""
        self.running = True
        
        for ingestor in self.ingestors:
            # Create task for continuous ingestion
            task = asyncio.create_task(
                ingestor.run_continuous(callback=self.handle_ingestion_result)
            )
            self.tasks.append(task)
            
            self.logger.info(f"Started ingestor: {ingestor.name}")
        
        self.logger.info(f"Started {len(self.ingestors)} ingestors")
    
    async def handle_ingestion_result(self, result: Any) -> None:
        """Handle ingestion results from ingestors."""
        try:
            self.logger.info(
                f"Ingestion result from {result.source}",
                record_count=result.record_count,
                success=result.success,
                timestamp=result.timestamp.isoformat()
            )
            
            # Process data through aggregator and store in database
            if hasattr(result, 'data') and result.data:
                for item in result.data:
                    # Process and store each item
                    storage_result = await self.aggregator.process_and_store(item)
                    
                    if not storage_result["success"]:
                        self.logger.warning(f"Storage failed for item: {storage_result.get('error', 'Unknown error')}")
                
                # Log aggregation statistics
                agg_stats = self.aggregator.get_summary_stats()
                self.logger.info(
                    "Data aggregation update",
                    total_records=agg_stats["total_records"],
                    by_type=agg_stats["by_type"]
                )
                
                # Store aggregation summary periodically
                if agg_stats["total_records"] % 100 == 0:  # Every 100 records
                    try:
                        await self.aggregator.store_aggregation_summary()
                    except Exception as e:
                        self.logger.error(f"Failed to store aggregation summary: {str(e)}")
            
            # Produce to Kafka (raw topic per type)
            if self.kafka_producer and hasattr(result, 'data') and result.data:
                for item in result.data:
                    item_type = item.get("type") or item.get("_type") or "unknown"
                    if item_type == "prediction":
                        topic = settings.kafka_topic_predictions
                        key = item.get("trip_id") or item.get("prediction_id")
                    elif item_type == "vehicle":
                        topic = settings.kafka_topic_vehicles
                        key = item.get("vehicle_id")
                    elif item_type == "alert":
                        topic = settings.kafka_topic_alerts
                        key = item.get("alert_id")
                    elif item_type == "trip_update":
                        topic = settings.kafka_topic_trip_updates
                        key = item.get("trip_id")
                    else:
                        continue
                    self.kafka_producer.produce_json(topic, key, item)
                self.kafka_producer.flush(1.0)
            
            # Run analytics if enabled
            if self.analytics_enabled and hasattr(result, 'data') and result.data:
                await self._run_analytics()
                
        except Exception as e:
            self.logger.error(f"Error handling ingestion result: {str(e)}", exc_info=True)
    
    async def _run_analytics(self) -> None:
        """Run analytics on recent data."""
        try:
            # Generate service summary every 100 records
            agg_stats = self.aggregator.get_summary_stats()
            if agg_stats["total_records"] % 100 == 0:
                service_summary = await transit_analytics.generate_service_summary()
                self.logger.info(
                    "Analytics update",
                    overall_status=service_summary["overall_status"],
                    on_time_percentage=service_summary["performance"]["on_time_percentage"],
                    anomaly_count=len(service_summary["anomalies"])
                )
                
                # Store analytics results
                try:
                    await self.aggregator.store_analytics_summary(service_summary)
                except Exception as e:
                    self.logger.error(f"Failed to store analytics summary: {str(e)}")
            
            # Run performance analysis every 50 records
            if agg_stats["total_records"] % 50 == 0:
                performance = await transit_analytics.analyze_performance()
                self.logger.info(
                    "Performance update",
                    on_time_percentage=performance.on_time_percentage,
                    average_delay_minutes=performance.average_delay / 60,
                    delayed_trips=performance.delayed_trips
                )
                
        except Exception as e:
            self.logger.error(f"Analytics error: {str(e)}", exc_info=True)
    
    async def stop_ingestors(self) -> None:
        """Stop all ingestors gracefully."""
        self.logger.info("Stopping ingestors...")
        self.running = False
        
        # Stop all ingestors
        for ingestor in self.ingestors:
            ingestor.stop()
        
        # Cancel all tasks
        for task in self.tasks:
            if not task.done():
                task.cancel()
        
        # Wait for tasks to complete
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)
        
        # Clean up sessions
        for ingestor in self.ingestors:
            if hasattr(ingestor, 'session') and ingestor.session:
                try:
                    await ingestor.session.close()
                except Exception as e:
                    self.logger.warning(f"Error cleaning up ingestor {ingestor.name} session: {e}")
        
        self.logger.info("All ingestors stopped")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on all components."""
        health_status = {
            "timestamp": datetime.utcnow().isoformat(),
            "status": "healthy" if self.running else "stopped",
            "ingestors": [],
            "aggregator": {},
            "storage": {},
            "analytics": {}
        }
        
        for ingestor in self.ingestors:
            try:
                ingestor_health = await ingestor.health_check()
                health_status["ingestors"].append(ingestor_health)
            except Exception as e:
                health_status["ingestors"].append({
                    "name": ingestor.name,
                    "status": "error",
                    "error": str(e)
                })
        
        # Add aggregator health information
        try:
            agg_stats = self.aggregator.get_summary_stats()
            health_status["aggregator"] = {
                "status": "healthy",
                "total_records": agg_stats["total_records"],
                "by_type": agg_stats["by_type"],
                "service_health": self.aggregator.get_service_health_summary()
            }
        except Exception as e:
            health_status["aggregator"] = {
                "status": "error",
                "error": str(e)
            }
        
        # Add storage health information
        try:
            # Get recent predictions to test storage connectivity
            recent_predictions = await self.aggregator.get_stored_recent_predictions(limit=5)
            health_status["storage"] = {
                "status": "healthy",
                "recent_records": len(recent_predictions),
                "connectivity": "ok"
            }
        except Exception as e:
            health_status["storage"] = {
                "status": "error",
                "error": str(e)
            }
        
        # Add analytics health information
        if self.analytics_enabled:
            try:
                # Test analytics functionality
                performance = await transit_analytics.analyze_performance()
                health_status["analytics"] = {
                    "status": "healthy",
                    "on_time_percentage": performance.on_time_percentage,
                    "total_trips": performance.total_trips
                }
            except Exception as e:
                health_status["analytics"] = {
                    "status": "error",
                    "error": str(e)
                }
        
        return health_status
    
    async def run(self) -> None:
        """Run the main pipeline."""
        try:
            # Initialize pipeline
            await self.initialize_pipeline()
            
            # Start ingestors
            await self.start_ingestors()
            
            # Keep running until interrupted
            while self.running:
                await asyncio.sleep(1)
                
                # Periodic health check and reporting
                if datetime.utcnow().second % 30 == 0:  # Every 30 seconds
                    health = await self.health_check()
                    self.logger.debug("Health check", health=health)
                    
                    # Generate and log aggregation reports
                    if self.aggregator.aggregations:
                        route_summary = self.aggregator.get_route_summary()
                        service_health = self.aggregator.get_service_health_summary()
                        
                        self.logger.info(
                            "Aggregation report",
                            route_count=len(route_summary),
                            service_status=service_health["service_status"],
                            delay_percentage=service_health["delay_percentage"]
                        )
                        
                        # Store aggregation summary in database
                        try:
                            await self.aggregator.store_aggregation_summary()
                        except Exception as e:
                            self.logger.error(f"Failed to store aggregation summary: {str(e)}")
                
        except KeyboardInterrupt:
            self.logger.info("Received interrupt signal")
        except Exception as e:
            self.logger.error(f"Pipeline error: {str(e)}", exc_info=True)
        finally:
            # Cleanup
            await self.stop_ingestors()
            self.logger.info("Pipeline shutdown complete")


async def main():
    """Main entry point."""
    pipeline = MBTAPipeline()
    
    # Setup signal handlers
    def signal_handler(signum, frame):
        """Handle shutdown signals."""
        pipeline.logger.info(f"Received signal {signum}")
        asyncio.create_task(pipeline.stop_ingestors())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        await pipeline.run()
    except Exception as e:
        pipeline.logger.error(f"Fatal error: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
