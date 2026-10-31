"""Unit Tests for Module 3: Logic Engine Violation Rules."""

import pytest
from src.cv.detector import DetectedObject
from src.cv.tracker import TrackedVehicle
from src.cv.traffic_light import TrafficLightState
from src.rules.red_light_rule import RedLightRule
from src.rules.wrong_way_rule import WrongWayRule
from src.rules.illegal_turn_rule import IllegalTurnRule
from src.rules.base_rule import ViolationType


def create_dummy_vehicle(track_id: int, trajectory_points: list) -> TrackedVehicle:
    """Helper to create a vehicle with a predefined trajectory."""
    p_init = trajectory_points[0]
    det = DetectedObject(
        bbox=(p_init[0] - 20, p_init[1] - 40, p_init[0] + 20, p_init[1]),
        confidence=0.92,
        class_id=2,
        class_name="car"
    )
    veh = TrackedVehicle(track_id, det)
    for p in trajectory_points[1:]:
        det_next = DetectedObject(
            bbox=(p[0] - 20, p[1] - 40, p[0] + 20, p[1]),
            confidence=0.92,
            class_id=2,
            class_name="car"
        )
        veh.update(det_next)
    return veh


def test_red_light_violation():
    """Verify red light violation triggers only on RED when crossing stop line."""
    stop_line = [[100, 500], [800, 500]]
    intersection_poly = [[50, 490], [850, 490], [850, 800], [50, 800]]

    rule = RedLightRule(stop_line, intersection_poly, min_crossing_depth_px=20)

    # Vehicle traveling downward: from y=480 (before stop line) to y=540 (past stop line)
    veh = create_dummy_vehicle(track_id=101, trajectory_points=[(400, 480), (400, 540)])

    # Case 1: Green light -> No violation
    v_green = rule.evaluate([veh], context={"traffic_light_state": TrafficLightState.GREEN}, frame_idx=1)
    assert len(v_green) == 0

    # Case 2: Red light -> Violation detected
    v_red = rule.evaluate([veh], context={"traffic_light_state": TrafficLightState.RED}, frame_idx=2)
    assert len(v_red) == 1
    assert v_red[0].violation_type == ViolationType.RED_LIGHT
    assert v_red[0].track_id == 101


def test_wrong_way_violation():
    """Verify wrong-way driving triggers when cos(theta) < -0.7."""
    lanes = [
        {
            "lane_id": 1,
            "name": "Làn chiều đi xuống (+y)",
            "polygon": [[100, 100], [500, 100], [500, 900], [100, 900]],
            "flow_vector": [0.0, 1.0] # Permitted direction: downward (+y)
        }
    ]

    rule = WrongWayRule(lanes, cosine_threshold=-0.70, min_continuous_frames=5, min_movement_px=20.0)

    # Vehicle traveling upwards (-y), against permitted flow
    trajectory = [(300, 800 - i * 15) for i in range(10)]
    veh = create_dummy_vehicle(track_id=202, trajectory_points=trajectory)

    # Evaluate across frames
    violations = []
    for f in range(6):
        v = rule.evaluate([veh], context={}, frame_idx=f)
        if v:
            violations.extend(v)

    assert len(violations) >= 1
    assert violations[0].violation_type == ViolationType.WRONG_WAY


def test_illegal_turn_violation():
    """Verify vehicle turning left from straight-only lane triggers illegal turn."""
    lanes = [
        {
            "lane_id": 2,
            "name": "Làn đi thẳng",
            "polygon": [[200, 200], [600, 200], [600, 800], [200, 800]],
            "allowed_directions": ["STRAIGHT"]
        }
    ]

    rule = IllegalTurnRule(lanes, min_trajectory_len=5, turn_angle_threshold=0.5)

    # Starts in lane at (400, 300), then turns sharply left (dx = -25 per step)
    trajectory = [(400 - i * 25, 300 + i * 5) for i in range(12)]
    veh = create_dummy_vehicle(track_id=303, trajectory_points=trajectory)

    violations = rule.evaluate([veh], context={}, frame_idx=10)
    assert len(violations) == 1
    assert violations[0].violation_type == ViolationType.ILLEGAL_TURN
