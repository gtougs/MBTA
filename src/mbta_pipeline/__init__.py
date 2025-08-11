"""MBTA Data Pipeline - Real-time transit data ingestion and analytics."""

__version__ = "0.1.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

from .config import settings
from .models import Prediction, VehiclePosition, TripUpdate, Alert
from .kafka.producer import KafkaProducerWrapper
from .kafka.consumer import KafkaConsumerWrapper

__all__ = [
    "settings",
    "Prediction",
    "VehiclePosition", 
    "TripUpdate",
    "Alert",
    "KafkaProducerWrapper",
    "KafkaConsumerWrapper",
]
