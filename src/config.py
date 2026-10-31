"""Global Application Configuration using Pydantic Settings."""

import os
from pathlib import Path
from typing import List, Tuple
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """Central configuration parameters for the system."""
    
    # Environment
    app_env: str = Field(default="development", alias="APP_ENV")
    app_name: str = Field(default="Traffic Violation Detection System", alias="APP_NAME")
    debug: bool = Field(default=True, alias="DEBUG")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # API & Networking
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    secret_key: str = Field(default="secret_token_change_in_production", alias="SECRET_KEY")

    # Video Ingestion
    default_rtsp_url: str = Field(default="data/sample_traffic.mp4", alias="DEFAULT_RTSP_URL")
    frame_width: int = Field(default=1920, alias="FRAME_WIDTH")
    frame_height: int = Field(default=1080, alias="FRAME_HEIGHT")
    target_fps: int = Field(default=30, alias="TARGET_FPS")

    # Inference & Models
    vehicle_detector_model: str = Field(default="yolov8n.pt", alias="VEHICLE_DETECTOR_MODEL")
    plate_detector_model: str = Field(default="models/checkpoints/plate_detector.pt", alias="PLATE_DETECTOR_MODEL")
    device: str = Field(default="cpu", alias="DEVICE")
    confidence_threshold: float = Field(default=0.45, alias="CONFIDENCE_THRESHOLD")
    iou_threshold: float = Field(default=0.50, alias="IOU_THRESHOLD")

    # Database
    database_url: str = Field(default="sqlite:///./traffic_violations.db", alias="DATABASE_URL")

    # Redis & Celery
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    celery_broker_url: str = Field(default="redis://localhost:6379/1", alias="CELERY_BROKER_URL")
    celery_result_backend: str = Field(default="redis://localhost:6379/2", alias="CELERY_RESULT_BACKEND")

    # Storage
    storage_backend: str = Field(default="local", alias="STORAGE_BACKEND")
    local_storage_dir: str = Field(default="./data/evidence", alias="LOCAL_STORAGE_DIR")
    s3_endpoint: str = Field(default="http://localhost:9000", alias="S3_ENDPOINT")
    s3_access_key: str = Field(default="minioadmin", alias="S3_ACCESS_KEY")
    s3_secret_key: str = Field(default="minioadmin", alias="S3_SECRET_KEY")
    s3_bucket_name: str = Field(default="traffic-evidence", alias="S3_BUCKET_NAME")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = AppSettings()
