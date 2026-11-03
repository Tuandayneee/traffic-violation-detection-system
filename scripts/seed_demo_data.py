"""Seed script to populate initial sample violations for immediate dashboard preview."""

import time
import json
from pathlib import Path
from src.backend.db.session import init_db, SessionLocal
from src.backend.db.models import ViolationRecord

DEMO_RECORDS = [
    {
        "event_id": "VIO-RLR-9A4B1C2D",
        "camera_id": "CAM_INTERSECTION_01",
        "violation_type": "RED_LIGHT_RUNNING",
        "vehicle_type": "car",
        "license_plate": "30A-888.88",
        "confidence": 0.94,
        "plate_confidence": 0.91,
        "status": "PENDING",
        "reviewer_notes": None,
        "snapshot_path": "data/evidence/demo_rlr.jpg",
        "plate_crop_path": "data/evidence/demo_plate_30a.jpg",
        "details": {"speed_kmh": 54, "light": "RED", "distance_past_line_m": 4.2}
    },
    {
        "event_id": "VIO-WWD-7E8F3D1A",
        "camera_id": "CAM_INTERSECTION_01",
        "violation_type": "WRONG_WAY_DRIVING",
        "vehicle_type": "motorcycle",
        "license_plate": "29-B1 678.90",
        "confidence": 0.89,
        "plate_confidence": 0.86,
        "status": "APPROVED",
        "reviewer_notes": "Xác nhận đi ngược chiều đường một chiều trên làn 1.",
        "snapshot_path": "data/evidence/demo_wwd.jpg",
        "plate_crop_path": "data/evidence/demo_plate_29b.jpg",
        "details": {"cos_theta": -0.89, "lane": "Làn 1", "direction": "Ngược chiều"}
    },
    {
        "event_id": "VIO-ILT-4C2E9F8B",
        "camera_id": "CAM_INTERSECTION_01",
        "violation_type": "ILLEGAL_TURN",
        "vehicle_type": "truck",
        "license_plate": "51C-777.12",
        "confidence": 0.96,
        "plate_confidence": 0.92,
        "status": "PENDING",
        "reviewer_notes": None,
        "snapshot_path": "data/evidence/demo_ilt.jpg",
        "plate_crop_path": "data/evidence/demo_plate_51c.jpg",
        "details": {"origin_lane": "Làn 2 (Chỉ đi thẳng)", "action": "Rẽ trái cấm"}
    }
]


def seed_database():
    init_db()
    db = SessionLocal()
    try:
        for rec in DEMO_RECORDS:
            existing = db.query(ViolationRecord).filter(ViolationRecord.event_id == rec["event_id"]).first()
            if not existing:
                row = ViolationRecord(
                    event_id=rec["event_id"],
                    camera_id=rec["camera_id"],
                    violation_type=rec["violation_type"],
                    vehicle_type=rec["vehicle_type"],
                    license_plate=rec["license_plate"],
                    confidence=rec["confidence"],
                    plate_confidence=rec["plate_confidence"],
                    status=rec["status"],
                    reviewer_notes=rec["reviewer_notes"],
                    snapshot_path=rec["snapshot_path"],
                    plate_crop_path=rec["plate_crop_path"],
                    metadata_json=json.dumps(rec["details"], ensure_ascii=False),
                    timestamp=time.time() - 3600
                )
                db.add(row)
        db.commit()
        print(f"Successfully seeded {len(DEMO_RECORDS)} demo violation records.")
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
