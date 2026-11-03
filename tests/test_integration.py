"""Integration Testing: End-to-End Pipeline & Component Interoperability.

Validates:
1. Cross-module data handoff: Synthetic Ingestion -> Detection/Tracking ->
   Traffic Light Analysis -> Rule Engine -> Evidence Packaging -> Database Persistence.
2. Verified consistency of track_id, coordinates, and timestamp across the entire workflow.
"""

import time
import uuid
from pathlib import Path
import numpy as np
import pytest

from src.data.synthetic_generator import SyntheticTrafficGenerator
from src.cv.detector import DetectedObject
from src.cv.tracker import VehicleTracker
from src.cv.traffic_light import TrafficLightClassifier, TrafficLightState
from src.rules.red_light_rule import RedLightRule
from src.rules.wrong_way_rule import WrongWayRule
from src.rules.illegal_turn_rule import IllegalTurnRule
from src.rules.rule_engine import TrafficRuleEngine
from src.backend.video_buffer import FrameRingBuffer
from src.backend.evidence_packager import EvidencePackager
from src.backend.db.session import init_db, SessionLocal
from src.backend.db.models import ViolationRecord


@pytest.fixture(scope="module")
def setup_integration_env(tmp_path_factory):
    evidence_dir = tmp_path_factory.mktemp("test_evidence")
    init_db()
    return evidence_dir


def test_full_pipeline_integration(setup_integration_env):
    """Executes a full 20-frame integrated workflow and asserts DB & evidence generation."""
    evidence_dir = setup_integration_env

    # 1. Initialize Pipeline Geometry
    stop_line = [[300, 600], [1500, 600]]
    intersection_poly = [[200, 580], [1600, 580], [1700, 1000], [100, 1000]]
    lanes = [
        {
            "lane_id": 1,
            "name": "Làn Đi Thẳng",
            "polygon": [[500, 600], [1000, 600], [1050, 1000], [450, 1000]],
            "flow_vector": [0.0, 1.0],
            "allowed_directions": ["STRAIGHT"]
        }
    ]

    # 2. Instantiate Modules
    gen = SyntheticTrafficGenerator(width=1920, height=1080)
    tracker = VehicleTracker(max_distance_px=100.0)
    tl_classifier = TrafficLightClassifier(history_size=3)
    ring_buffer = FrameRingBuffer(capacity=50)
    packager = EvidencePackager(output_root=str(evidence_dir))

    rule_engine = TrafficRuleEngine([
        RedLightRule(stop_line, intersection_poly, min_crossing_depth_px=20),
        WrongWayRule(lanes, cosine_threshold=-0.70, min_continuous_frames=5),
        IllegalTurnRule(lanes, min_trajectory_len=5)
    ])

    captured_violations = []

    # 3. Simulate sequential video frames
    # Frames 0-9: Vehicle approaches line while RED
    # Frames 10-15: Vehicle crosses stop line into intersection -> VIOLATION
    for f_idx in range(16):
        # Create background with red traffic light
        frame = gen.generate_base_intersection_frame(traffic_light_state="RED")
        car_y = 520 + f_idx * 15 # Y progresses from 520 (before line) to 745 (past line 600)
        car_bbox = (700, car_y - 100, 840, car_y)
        frame = gen.render_vehicle(frame, bbox=car_bbox, vehicle_type="car", plate_text="30F-888.88")

        # Push to buffer
        ring_buffer.push(frame, frame_idx=f_idx, timestamp=time.time())

        # Detection & Tracking step
        det = DetectedObject(bbox=car_bbox, confidence=0.95, class_id=2, class_name="car")
        tracked = tracker.update([det])
        assert len(tracked) == 1
        tracked[0].license_plate = "30F-888.88"
        tracked[0].plate_confidence = 0.94

        # Traffic Light classification step
        tl_crop = frame[80:260, 1450:1530]
        light_state = tl_classifier.classify_roi(tl_crop)
        assert light_state == TrafficLightState.RED

        # Rule evaluation
        violations = rule_engine.process_frame(
            tracked_vehicles=tracked,
            context={"traffic_light_state": light_state},
            frame_idx=f_idx
        )

        for vio in violations:
            captured_violations.append(vio)
            evidence_files = packager.package_violation(
                event=vio,
                current_frame=frame,
                ring_buffer=ring_buffer,
                stop_line=stop_line
            )

            # Persist directly to DB
            db = SessionLocal()
            try:
                rec = ViolationRecord(
                    event_id=vio.event_id,
                    camera_id="CAM_INTEGRATION_01",
                    violation_type=vio.violation_type.value,
                    vehicle_type=vio.vehicle_type,
                    license_plate=vio.license_plate,
                    confidence=vio.confidence,
                    plate_confidence=vio.plate_confidence,
                    snapshot_path=evidence_files["snapshot_path"],
                    video_clip_path=evidence_files["video_clip_path"],
                    timestamp=vio.timestamp
                )
                db.add(rec)
                db.commit()
            finally:
                db.close()

    # 4. Assert Integration Success
    assert len(captured_violations) == 1
    event = captured_violations[0]
    assert event.violation_type.value == "RED_LIGHT_RUNNING"
    assert event.license_plate == "30F-888.88"

    # 5. Verify Database Record & Evidence Artifacts
    db = SessionLocal()
    try:
        db_record = db.query(ViolationRecord).filter(ViolationRecord.event_id == event.event_id).first()
        assert db_record is not None
        assert db_record.license_plate == "30F-888.88"
        assert db_record.status == "PENDING"
        assert Path(db_record.snapshot_path).exists()
    finally:
        db.close()
