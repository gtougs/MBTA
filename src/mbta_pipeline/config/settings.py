"""Configuration settings for MBTA Data Pipeline."""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # MBTA API Configuration
    mbta_api_key: str = Field(..., env="MBTA_API_KEY")
    mbta_base_url: str = Field("https://api-v3.mbta.com", env="MBTA_BASE_URL")
    mbta_gtfs_rt_base_url: str = Field("https://cdn.mbta.com/realtime", env="MBTA_GTFS_RT_BASE_URL")
    
    # MBTA API Endpoints
    mbta_endpoint_predictions: str = Field("/predictions", env="MBTA_ENDPOINT_PREDICTIONS")
    mbta_endpoint_vehicles: str = Field("/vehicles", env="MBTA_ENDPOINT_VEHICLES")
    mbta_endpoint_alerts: str = Field("/alerts", env="MBTA_ENDPOINT_ALERTS")
    mbta_endpoint_routes: str = Field("/routes", env="MBTA_ENDPOINT_ROUTES")
    mbta_endpoint_stops: str = Field("/stops", env="MBTA_ENDPOINT_STOPS")
    mbta_endpoint_trips: str = Field("/trips", env="MBTA_ENDPOINT_TRIPS")
    
    # Database Configuration
    database_url: str = Field("postgresql://localhost:5432/mbta_data", env="DATABASE_URL")
    database_pool_size: int = Field(10, env="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(20, env="DATABASE_MAX_OVERFLOW")
    database_echo: bool = Field(False, env="DATABASE_ECHO")
    
    # Redis Configuration (for caching and rate limiting)
    redis_url: str = Field("redis://localhost:6379/0", env="REDIS_URL")
    redis_cache_ttl_seconds: int = Field(300, env="REDIS_CACHE_TTL_SECONDS")
    
    # Kafka Configuration
    kafka_bootstrap_servers: str = Field("localhost:9092", env="KAFKA_BOOTSTRAP_SERVERS")
    kafka_topic_predictions: str = Field("mbta.predictions.raw", env="KAFKA_TOPIC_PREDICTIONS")
    kafka_topic_vehicles: str = Field("mbta.vehicles.raw", env="KAFKA_TOPIC_VEHICLES")
    kafka_topic_alerts: str = Field("mbta.alerts.raw", env="KAFKA_TOPIC_ALERTS")
    kafka_topic_trip_updates: str = Field("mbta.trip_updates.raw", env="KAFKA_TOPIC_TRIP_UPDATES")
    
    # BigQuery Configuration
    google_application_credentials: Optional[str] = Field(None, env="GOOGLE_APPLICATION_CREDENTIALS")
    bigquery_project_id: Optional[str] = Field(None, env="BIGQUERY_PROJECT_ID")
    bigquery_dataset: str = Field("mbta_data", env="BIGQUERY_DATASET")
    bigquery_location: str = Field("US", env="BIGQUERY_LOCATION")
    
    # Application Configuration
    log_level: str = Field("INFO", env="LOG_LEVEL")
    polling_interval_seconds: int = Field(15, env="POLLING_INTERVAL_SECONDS")
    batch_size: int = Field(100, env="BATCH_SIZE")
    max_retries: int = Field(3, env="MAX_RETRIES")
    retry_delay_seconds: int = Field(5, env="RETRY_DELAY_SECONDS")
    
    # Rate Limiting
    mbta_rate_limit_requests_per_minute: int = Field(1000, env="MBTA_RATE_LIMIT_REQUESTS_PER_MINUTE")
    mbta_rate_limit_burst_size: int = Field(100, env="MBTA_RATE_LIMIT_BURST_SIZE")
    
    # Data Processing
    enable_anomaly_detection: bool = Field(True, env="ENABLE_ANOMALY_DETECTION")
    anomaly_detection_z_score_threshold: float = Field(2.5, env="ANOMALY_DETECTION_Z_SCORE_THRESHOLD")
    headway_bunching_threshold: float = Field(0.5, env="HEADWAY_BUNCHING_THRESHOLD")
    auto_seed_missing_entities: bool = Field(True, env="AUTO_SEED_MISSING_ENTITIES")
    
    # Monitoring
    enable_metrics: bool = Field(True, env="ENABLE_METRICS")
    metrics_port: int = Field(9090, env="METRICS_PORT")
    prometheus_endpoint: str = Field("/metrics", env="PROMETHEUS_ENDPOINT")
    
    # Development
    debug: bool = Field(False, env="DEBUG")
    environment: str = Field("development", env="ENVIRONMENT")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "allow"


# Global settings instance
settings = Settings()
