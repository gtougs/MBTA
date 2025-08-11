"""MBTA Pipeline Models Package."""

from .base import BaseModel
from .transit import Prediction, VehiclePosition, TripUpdate, Alert
from .database import (
    Route, Stop, Trip, Vehicle, VehiclePosition as DBVehiclePosition,
    Prediction as DBPrediction, TripUpdate as DBTripUpdate, Alert as DBAlert,
    DataIngestionLog
)

__all__ = [
    # Base models
    "BaseModel",
    
    # Transit models (for API responses)
    "Prediction", 
    "VehiclePosition", 
    "TripUpdate", 
    "Alert",
    
    # Database models
    "Route",
    "Stop", 
    "Trip",
    "Vehicle",
    "DBVehiclePosition",
    "DBPrediction",
    "DBTripUpdate", 
    "DBAlert",
    "DataIngestionLog",
]
