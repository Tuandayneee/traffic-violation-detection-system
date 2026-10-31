"""Celery Background Worker Tasks."""

import json
from loguru import logger
from .celery_app import celery_app
from .db.session import SessionLocal
from .db.models import ViolationRecord


@celery_app.task(name="record_violation_task")
def record_violation_task(violation_dict: dict) -> dict:
    """Persists violation event into PostgreSQL asynchronously."""
    db = SessionLocal()
    try:
        record = ViolationRecord(
            event_id=violation_dict["event_id"],
            camera_id=violation_dict.get("camera_id", "CAM_INTERSECTION_01"),
            violation_type=violation_dict["violation_type"],
            vehicle_type=violation_dict.get("vehicle_type", "car"),
            license_plate=violation_dict.get("license_plate"),
            confidence=violation_dict.get("confidence", 0.0),
            plate_confidence=violation_dict.get("plate_confidence", 0.0),
            status="PENDING",
            snapshot_path=violation_dict.get("snapshot_path"),
            plate_crop_path=violation_dict.get("plate_crop_path"),
            video_clip_path=violation_dict.get("video_clip_path"),
            metadata_json=json.dumps(violation_dict.get("details", {})),
            timestamp=violation_dict.get("timestamp")
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        logger.info(f"Recorded violation in DB: {record.event_id} (ID: {record.id})")
        return {"status": "SUCCESS", "id": record.id, "event_id": record.event_id}
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to record violation: {e}")
        return {"status": "ERROR", "error": str(e)}
    finally:
        db.close()
