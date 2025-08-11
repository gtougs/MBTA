"""Base ingestor class for all data sources."""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, AsyncGenerator
from datetime import datetime, timedelta
from dataclasses import dataclass

from ..config.settings import settings
from ..utils.logging import get_logger


@dataclass
class IngestionResult:
    """Result of a data ingestion operation."""
    
    success: bool
    data: List[Dict[str, Any]]
    timestamp: datetime
    source: str
    record_count: int
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    @property
    def is_successful(self) -> bool:
        """Check if ingestion was successful."""
        return self.success and self.record_count > 0


class BaseIngestor(ABC):
    """Abstract base class for all data ingestors."""
    
    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        """Initialize the ingestor."""
        self.name = name
        self.config = config or {}
        self.logger = get_logger(f"{self.__class__.__name__}.{name}")
        
        # Configuration
        self.polling_interval = self.config.get(
            "polling_interval", 
            settings.polling_interval_seconds
        )
        self.max_retries = self.config.get("max_retries", settings.max_retries)
        self.retry_delay = self.config.get("retry_delay", settings.retry_delay_seconds)
        
        # State
        self.is_running = False
        self.last_successful_ingestion = None
        self.total_records_ingested = 0
        self.total_errors = 0
        self.consecutive_failures = 0
        
    @abstractmethod
    async def fetch_data(self) -> List[Dict[str, Any]]:
        """Fetch data from the source. Must be implemented by subclasses."""
        pass
    
    @abstractmethod
    async def transform_data(self, raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform raw data into standardized format. Must be implemented by subclasses."""
        pass
    
    async def ingest(self) -> IngestionResult:
        """Perform a single ingestion cycle."""
        start_time = datetime.utcnow()
        
        try:
            # Fetch raw data
            self.logger.info(f"Starting data ingestion for {self.name}")
            raw_data = await self.fetch_data()
            
            if not raw_data:
                self.logger.warning(f"No data received from {self.name}")
                return IngestionResult(
                    success=True,
                    data=[],
                    timestamp=start_time,
                    source=self.name,
                    record_count=0
                )
            
            # Transform data
            transformed_data = await self.transform_data(raw_data)
            
            # Update metrics
            self.total_records_ingested += len(transformed_data)
            self.last_successful_ingestion = start_time
            self.consecutive_failures = 0
            
            self.logger.info(
                f"Successfully ingested {len(transformed_data)} records from {self.name}"
            )
            
            return IngestionResult(
                success=True,
                data=transformed_data,
                timestamp=start_time,
                source=self.name,
                record_count=len(transformed_data),
                metadata={
                    "raw_record_count": len(raw_data),
                    "transformed_record_count": len(transformed_data),
                    "processing_time_ms": (datetime.utcnow() - start_time).total_seconds() * 1000
                }
            )
            
        except Exception as e:
            self.total_errors += 1
            self.consecutive_failures += 1
            
            self.logger.error(
                f"Error during ingestion from {self.name}: {str(e)}", 
                exc_info=True
            )
            
            return IngestionResult(
                success=False,
                data=[],
                timestamp=start_time,
                source=self.name,
                record_count=0,
                error_message=str(e)
            )
    
    async def run_continuous(self, callback: Optional[callable] = None) -> None:
        """Run continuous ingestion with the specified polling interval."""
        self.is_running = True
        self.logger.info(f"Starting continuous ingestion for {self.name}")
        
        try:
            while self.is_running:
                # Perform ingestion
                result = await self.ingest()
                
                # Call callback if provided
                if callback and result.is_successful:
                    await callback(result)
                
                # Wait for next cycle
                await asyncio.sleep(self.polling_interval)
                
        except asyncio.CancelledError:
            self.logger.info(f"Ingestion cancelled for {self.name}")
        except Exception as e:
            self.logger.error(f"Unexpected error in continuous ingestion: {str(e)}", exc_info=True)
        finally:
            self.is_running = False
            self.logger.info(f"Stopped continuous ingestion for {self.name}")
    
    def stop(self) -> None:
        """Stop continuous ingestion."""
        self.is_running = False
        self.logger.info(f"Stopping ingestion for {self.name}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform a health check on the ingestor."""
        return {
            "name": self.name,
            "is_running": self.is_running,
            "last_successful_ingestion": self.last_successful_ingestion,
            "total_records_ingested": self.total_records_ingested,
            "total_errors": self.total_errors,
            "consecutive_failures": self.consecutive_failures,
            "status": "healthy" if self.consecutive_failures < 5 else "degraded"
        }
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics for the ingestor."""
        return {
            "name": self.name,
            "total_records_ingested": self.total_records_ingested,
            "total_errors": self.total_errors,
            "consecutive_failures": self.consecutive_failures,
            "last_successful_ingestion": self.last_successful_ingestion,
            "polling_interval": self.polling_interval
        }
