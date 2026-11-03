"""End-to-End Traffic Violation Pipeline Execution Runner.

Simulates a real-world RTSP camera stream, runs:
1. Frame Ingestion & Synthetic rendering
2. Vehicle Detection & ByteTrack tracking
3. Traffic Light State classification
4. Rule Engine evaluation (Red Light, Wrong-Way, Illegal Turn)
5. Evidence packaging & Database commit
"""

import time
import argparse
from pathlib import Path
from loguru import logger

from src.data.synthetic_generator import SyntheticTrafficGenerator
from src.cv.detector import VehicleDetector, DetectedObject
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


def run_pipeline(num_frames: int = 150):
    logger.info("Initializing Traffic Violation Pipeline...")
    init_db()

    # Geometry Setup
    stop_line = [[400, 720], [1520, 720]]
    intersection_poly = [[300, 700], [1620, 700], [1820, 1080], [100, 1080]]
    lanes = [
        {
            "lane_id": 1,
            "name": "Làn 1",
            "polygon": [[400, 720], [750, 720], [600, 1080], [100, 1080]],
            "flow_vector": [0.0, 1.0],
            "allowed_directions": ["LEFT"]
        },
        {
            "lane_id": 2,
            "name": "Làn 2",
            "polygon": [[750, 720], [1120, 720], [1180, 1080], [600, 1080]],
            "flow_vector": [0.0, 1.0],
            "allowed_directions": ["STRAIGHT"]
        }
    ]

    # Components
    generator = SyntheticTrafficGenerator(width=1920, height=1080)
    tracker = VehicleTracker(max_distance_px=95.0)
    tl_classifier = TrafficLightClassifier(history_size=3)

    # Rules
    rule_engine = TrafficRuleEngine([
        RedLightRule(stop_line, intersection_poly, min_crossing_depth_px=20),
        WrongWayRule(lanes, cosine_threshold=-0.70, min_continuous_frames=5),
        IllegalTurnRule(lanes, min_trajectory_len=6, turn_angle_threshold=0.50),
    ])

    ring_buffer = FrameRingBuffer(capacity=150)
    packager = EvidencePackager(output_root="./data/evidence")

    logger.info(f"Running simulation for {num_frames} frames...")

    for f_idx in range(num_frames):
        # 1. Simulate traffic light (Red from frame 40 onwards)
        light_state_str = "RED" if f_idx >= 40 else "GREEN"
        frame = generator.generate_base_intersection_frame(traffic_light_state=light_state_str)

        # 2. Simulate moving vehicle: Car 1 crossing stop line during RED
        car_y = 660 + (f_idx - 35) * 8 if f_idx >= 35 else 660
        frame = generator.render_vehicle(frame, bbox=(850, car_y - 120, 990, car_y), vehicle_type="car", plate_text="29A-999.99")

        # Push to ring buffer
        ring_buffer.push(frame, frame_idx=f_idx, timestamp=time.time())

        # 3. Simulate Detection & Tracking
        det = DetectedObject(bbox=(850, car_y - 120, 990, car_y), confidence=0.93, class_id=2, class_name="car")
        tracked = tracker.update([det])
        tracked[0].license_plate = "29A-999.99"
        tracked[0].plate_confidence = 0.95

        # 4. Classify traffic light from ROI
        tl_crop = frame[80:260, 1450:1530]
        active_tl = tl_classifier.classify_roi(tl_crop)

        # 5. Evaluate Rules
        violations = rule_engine.process_frame(
            tracked_vehicles=tracked,
            context={"traffic_light_state": active_tl},
            frame_idx=f_idx
        )

        # 6. If violation detected, package evidence & save to DB
        for vio in violations:
            logger.warning(f"[VIOLATION DETECTED] Frame {f_idx}: {vio.violation_type} | Vehicle {vio.track_id} | Plate: {vio.license_plate}")
            evidence = packager.package_violation(
                event=vio,
                current_frame=frame,
                ring_buffer=ring_buffer,
                stop_line=stop_line
            )

            # Persist to database
            db = SessionLocal()
            try:
                rec = ViolationRecord(
                    event_id=vio.event_id,
                    violation_type=vio.violation_type.value,
                    vehicle_type=vio.vehicle_type,
                    license_plate=vio.license_plate,
                    confidence=vio.confidence,
                    plate_confidence=vio.plate_confidence,
                    snapshot_path=evidence["snapshot_path"],
                    video_clip_path=evidence["video_clip_path"],
                    timestamp=vio.timestamp
                )
                db.add(rec)
                db.commit()
                logger.success(f"Recorded ticket to DB: {vio.event_id}")
            finally:
                db.close()

    logger.info("Pipeline simulation run completed successfully.")


if __name__ == "__main__":
    run_pipeline(num_frames=80)
