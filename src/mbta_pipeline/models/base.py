"""Base model class for all data models."""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel as PydanticBaseModel, Field


class BaseModel(PydanticBaseModel):
    """Base model with common fields and methods."""
    
    # Metadata fields
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    source: str = Field(..., description="Data source identifier")
    version: str = Field("1.0", description="Data model version")
    
    # Processing metadata
    processed_at: Optional[datetime] = None
    batch_id: Optional[str] = None
    partition_date: Optional[str] = None
    
    # Quality metrics
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    data_quality_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        validate_assignment = True
    
    def update_timestamp(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.utcnow()
    
    def set_processed(self, batch_id: str, partition_date: str) -> None:
        """Mark record as processed."""
        self.processed_at = datetime.utcnow()
        self.batch_id = batch_id
        self.partition_date = partition_date
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return self.dict()
    
    def get_partition_key(self) -> str:
        """Get partition key for storage."""
        if self.partition_date:
            return self.partition_date
        return self.created_at.strftime("%Y-%m-%d")
