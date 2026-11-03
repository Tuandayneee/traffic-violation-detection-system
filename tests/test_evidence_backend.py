"""Unit Tests for Module 4: Evidence Packaging & Backend API."""

import json
from pathlib import Path
import numpy as np
import pytest
from fastapi.testclient import TestClient

from src.backend.video_buffer import FrameRingBuffer
from src.backend.evidence_packager import EvidencePackager
from src.rules.base_rule import ViolationEvent, ViolationType
from src.backend.api.main import app
from src.backend.db.session import init_db, SessionLocal
from src.backend.db.models import ViolationRecord


@pytest.fixture(scope="module")
def client():
    """TestClient fixture with initialized test SQLite database."""
    init_db()
    with TestClient(app) as c:
        yield c


def test_frame_ring_buffer(tmp_path):
    """Verify push and export of frames to mp4 video."""
    buffer = FrameRingBuffer(capacity=10)
    for i in range(5):
        frame = np.full((120, 160, 3), i * 40, dtype=np.uint8)
        buffer.push(frame, frame_idx=i, timestamp=float(i))

    out_file = tmp_path / "test_clip.mp4"
    success = buffer.export_video_clip(str(out_file), fps=10)
    assert success is True
    assert out_file.exists()


def test_evidence_packager(tmp_path):
    """Verify evidence packaging of snapshot, plate crop, and metadata JSON."""
    packager = EvidencePackager(output_root=str(tmp_path))

    event = ViolationEvent(
        event_id="TEST-VIO-001",
        track_id=42,
        violation_type=ViolationType.RED_LIGHT,
        timestamp=1700000000.0,
        frame_idx=100,
        confidence=0.95,
        vehicle_type="car",
        bbox=(50, 60, 150, 180),
        license_plate="29A-123.45",
        plate_confidence=0.88,
        details={"speed": 45}
    )

    frame = np.zeros((300, 400, 3), dtype=np.uint8)
    plate = np.full((30, 80, 3), 255, dtype=np.uint8)

    results = packager.package_violation(event, current_frame=frame, plate_crop=plate)

    assert Path(results["snapshot_path"]).exists()
    assert Path(results["plate_crop_path"]).exists()
    assert Path(results["metadata_path"]).exists()

    with open(results["metadata_path"], "r") as f:
        meta = json.load(f)
    assert meta["event_id"] == "TEST-VIO-001"
    assert meta["license_plate"] == "29A-123.45"


def test_api_health_and_violations(client):
    """Verify FastAPI endpoints return expected schemas."""
    # Health check
    res = client.get("/healthz")
    assert res.status_code == 200
    assert res.json()["status"] == "HEALTHY"

    # Insert a dummy record with unique ID
    import uuid
    unique_event_id = f"API-TEST-{uuid.uuid4().hex[:8]}"
    db = SessionLocal()
    record = ViolationRecord(
        event_id=unique_event_id,
        violation_type="RED_LIGHT_RUNNING",
        license_plate="30F-999.99",
        status="PENDING"
    )
    db.add(record)
    db.commit()
    db.close()

    # List violations
    res_list = client.get("/api/violations")
    assert res_list.status_code == 200
    data = res_list.json()
    assert data["total"] >= 1
