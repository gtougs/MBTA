"""Base processor class for MBTA transit data processing."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from datetime import datetime
import logging

from ..models.transit import (
    Stop, Route, Trip, Prediction, 
    VehiclePosition, TripUpdate, Alert
)

logger = logging.getLogger(__name__)


class BaseProcessor(ABC):
    """Base class for all data processors."""
    
    def __init__(self, name: str):
        """Initialize processor with a name."""
        self.name = name
        self.processed_count = 0
        self.error_count = 0
        self.start_time = None
        
    def __enter__(self):
        """Context manager entry."""
        self.start_time = datetime.now()
        logger.info(f"Starting {self.name} processor")
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with statistics."""
        if self.start_time:
            duration = datetime.now() - self.start_time
            logger.info(
                f"Completed {self.name} processor: "
                f"{self.processed_count} processed, "
                f"{self.error_count} errors, "
                f"duration: {duration.total_seconds():.2f}s"
            )
    
    @abstractmethod
    def process(self, data: Any) -> Any:
        """Process the input data and return processed result."""
        pass
    
    def process_batch(self, data_list: List[Any]) -> List[Any]:
        """Process a batch of data items."""
        results = []
        for item in data_list:
            try:
                result = self.process(item)
                if result is not None:
                    results.append(result)
                self.processed_count += 1
            except Exception as e:
                logger.error(f"Error processing item in {self.name}: {e}")
                self.error_count += 1
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """Get processing statistics."""
        return {
            "processor": self.name,
            "processed_count": self.processed_count,
            "error_count": self.error_count,
            "success_rate": (
                self.processed_count / (self.processed_count + self.error_count)
                if (self.processed_count + self.error_count) > 0 else 0
            )
        }
