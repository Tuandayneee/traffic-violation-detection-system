"""Non-Functional Testing: Performance, Stability, Resilience & Concurrency.

Benchmarking metrics:
1. Latency & Throughput (FPS): Evaluates tracking and geometric rules on 100 frames (Target >= 30 FPS).
2. Memory Footprint & Ring Buffer Stability: Verifies rolling buffer retains strict bounded memory over 1,000 pushes.
3. Fault Tolerance & Exception Resilience: Feeds malformed boxes, out-of-bounds coordinates, and None values.
4. Concurrency & Stress: Verifies FastAPI throughput under multi-threaded load.
"""

import time
import concurrent.futures
import numpy as np
import pytest
from fastapi.testclient import TestClient

from src.cv.detector import DetectedObject
from src.cv.tracker import VehicleTracker
from src.cv.traffic_light import TrafficLightClassifier
from src.rules.red_light_rule import RedLightRule
from src.rules.wrong_way_rule import WrongWayRule
from src.rules.illegal_turn_rule import IllegalTurnRule
from src.rules.rule_engine import TrafficRuleEngine
from src.backend.video_buffer import FrameRingBuffer
from src.backend.api.main import app
from src.backend.db.session import init_db


def test_latency_and_throughput_fps_benchmark():
    """Benchmark: Measures latency per frame and effective FPS."""
    stop_line = [[200, 500], [1400, 500]]
    intersection_poly = [[150, 480], [1450, 480], [1500, 900], [100, 900]]
    lanes = [
        {
            "lane_id": 1,
            "polygon": [[200, 500], [800, 500], [850, 900], [150, 900]],
            "flow_vector": [0.0, 1.0],
            "allowed_directions": ["STRAIGHT"]
        }
    ]

    tracker = VehicleTracker(max_distance_px=100.0)
    tl_classifier = TrafficLightClassifier(history_size=3)
    engine = TrafficRuleEngine([
        RedLightRule(stop_line, intersection_poly),
        WrongWayRule(lanes),
        IllegalTurnRule(lanes)
    ])

    num_frames = 100
    latencies = []

    # Prepare dummy crops and detections
    tl_crop = np.zeros((60, 40, 3), dtype=np.uint8)
    tl_crop[:, :] = (0, 0, 255) # Red

    for i in range(num_frames):
        t0 = time.perf_counter()

        # Detection simulating 4 vehicles
        detections = [
            DetectedObject((100 + j * 200, 300 + i * 4, 180 + j * 200, 420 + i * 4), 0.9, 2, "car")
            for j in range(4)
        ]

        # Tracker step
        tracked = tracker.update(detections)

        # Traffic light step
        tl_state = tl_classifier.classify_roi(tl_crop)

        # Rule engine step
        engine.process_frame(tracked, {"traffic_light_state": tl_state}, frame_idx=i)

        t1 = time.perf_counter()
        latencies.append((t1 - t0) * 1000) # ms

    avg_latency_ms = float(np.mean(latencies))
    effective_fps = 1000.0 / avg_latency_ms

    print(f"\n[BENCHMARK] Avg Latency: {avg_latency_ms:.2f} ms/frame | Throughput: {effective_fps:.1f} FPS")

    # Assert real-time edge criteria: processing must exceed 30 FPS (> 30 fps means < 33.3ms)
    assert avg_latency_ms < 33.3, f"Average latency too high: {avg_latency_ms:.2f}ms"
    assert effective_fps >= 30.0, f"Throughput below real-time threshold: {effective_fps:.1f} FPS"


def test_memory_stability_bounded_buffer():
    """Stability: Asserts FrameRingBuffer strictly respects capacity over 1,000 pushes."""
    capacity = 150
    buffer = FrameRingBuffer(capacity=capacity)
    dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)

    for i in range(1000):
        buffer.push(dummy_frame, frame_idx=i, timestamp=float(i))

    # Internal buffer must never exceed maxlen capacity
    assert len(buffer._buffer) == capacity


def test_resilience_to_malformed_inputs():
    """Resilience: Verifies pipeline never crashes on out-of-bound / corrupt inputs."""
    tracker = VehicleTracker()
    rule = RedLightRule([[0, 500], [1000, 500]], [[0, 500], [1000, 500], [1000, 1000], [0, 1000]])

    # 1. Out-of-bounds coordinates
    det_oob = DetectedObject((-500, -200, 99999, 88888), 0.5, 2, "car")
    tracks = tracker.update([det_oob])
    assert len(tracks) >= 1

    # 2. Inverted bounding box (x2 < x1)
    det_inverted = DetectedObject((400, 300, 200, 100), 0.8, 2, "car")
    tracks_inv = tracker.update([det_inverted])
    assert len(tracks_inv) >= 1

    # 3. Rule evaluation with empty / None context
    violations = rule.evaluate(tracks_inv, context={}, frame_idx=99)
    assert isinstance(violations, list)


def test_concurrent_api_stress():
    """Concurrency: Asserts backend handles concurrent requests without dropped connections."""
    init_db()
    client = TestClient(app)

    def send_request():
        res = client.get("/api/violations/stats/summary")
        return res.status_code

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(send_request) for _ in range(40)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    assert all(code == 200 for code in results), "All concurrent requests must return HTTP 200 OK."
