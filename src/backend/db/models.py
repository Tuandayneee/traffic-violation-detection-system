"""SQLAlchemy Models for Traffic Violations & Camera Configurations."""

import time
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean
from sqlalchemy.orm import declarative_base

Base = declarative_base()


def utc_now():
    return datetime.now(timezone.utc)


class ViolationRecord(Base):
    """Stores verified and pending traffic violation tickets."""
    __tablename__ = "violations"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String(64), unique=True, index=True, nullable=False)
    camera_id = Column(String(64), index=True, default="CAM_INTERSECTION_01")
    violation_type = Column(String(64), index=True, nullable=False)
    vehicle_type = Column(String(32), default="car")
    license_plate = Column(String(32), index=True, nullable=True)
    confidence = Column(Float, default=0.0)
    plate_confidence = Column(Float, default=0.0)

    # Review Status: PENDING, APPROVED, REJECTED
    status = Column(String(32), default="PENDING", index=True)
    reviewer_notes = Column(Text, nullable=True)

    # Artifact paths
    snapshot_path = Column(String(255), nullable=True)
    plate_crop_path = Column(String(255), nullable=True)
    video_clip_path = Column(String(255), nullable=True)
    metadata_json = Column(Text, nullable=True)

    timestamp = Column(Float, default=time.time)
    created_at = Column(DateTime, default=utc_now)


class CameraConfig(Base):
    """Stores intersection camera calibration and ROI settings."""
    __tablename__ = "cameras"

    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(String(64), unique=True, index=True, nullable=False)
    name = Column(String(128), nullable=False)
    source_url = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    roi_config_json = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
