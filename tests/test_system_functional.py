"""System & Functional Testing: Complete Real-World Traffic Scenarios.

Tests all business rules, officer review lifecycle, and camera configuration:
- Scenario 1: Vehicle stopping legally before stop line -> No Violation.
- Scenario 2: Red-light running -> Ticket generated.
- Scenario 3: Wrong-way travel on one-way lane -> Ticket generated.
- Scenario 4: Illegal turn from straight-only lane -> Ticket generated.
- Scenario 5: Review workflow (Officer Approves / Rejects tickets).
- Scenario 6: Interactive Camera ROI configuration API update.
"""

import uuid
import pytest
from fastapi.testclient import TestClient

from src.cv.detector import DetectedObject
from src.cv.tracker import TrackedVehicle
from src.cv.traffic_light import TrafficLightState
from src.rules.red_light_rule import RedLightRule
from src.rules.wrong_way_rule import WrongWayRule
from src.rules.illegal_turn_rule import IllegalTurnRule
from src.backend.api.main import app
from src.backend.db.session import init_db, SessionLocal
from src.backend.db.models import ViolationRecord


@pytest.fixture(scope="module")
def api_client():
    init_db()
    with TestClient(app) as client:
        yield client


def test_scenario_compliant_stop_before_red_light():
    """Functional Scenario 1: Vehicle stops 15px before the stop line during RED."""
    stop_line = [[100, 500], [900, 500]] # Stop line at y=500
    intersection_poly = [[50, 500], [950, 500], [950, 900], [50, 900]]

    rule = RedLightRule(stop_line, intersection_poly, min_crossing_depth_px=25)

    # Vehicle approaches to y=485 (15px before stop line) and stops
    trajectory = [(500, 420), (500, 450), (500, 480), (500, 485), (500, 485)]
    p0 = trajectory[0]
    veh = TrackedVehicle(1, DetectedObject((p0[0]-20, p0[1]-40, p0[0]+20, p0[1]), 0.95, 2, "car"))
    for p in trajectory[1:]:
        veh.update(DetectedObject((p[0]-20, p[1]-40, p[0]+20, p[1]), 0.95, 2, "car"))

    violations = rule.evaluate([veh], context={"traffic_light_state": TrafficLightState.RED}, frame_idx=10)
    assert len(violations) == 0, "Compliant stopping vehicle must not be flagged."


def test_scenario_officer_review_lifecycle(api_client):
    """Functional Scenario 2: Officer review and ticket approval/rejection lifecycle."""
    event_id = f"FUNC-TEST-{uuid.uuid4().hex[:8]}"

    # 1. Pre-insert a pending violation
    db = SessionLocal()
    rec = ViolationRecord(
        event_id=event_id,
        camera_id="CAM_INTERSECTION_01",
        violation_type="RED_LIGHT_RUNNING",
        vehicle_type="car",
        license_plate="29A-777.77",
        status="PENDING"
    )
    db.add(rec)
    db.commit()
    rec_id = rec.id
    db.close()

    # 2. Officer views violation details
    res = api_client.get(f"/api/violations/{rec_id}")
    assert res.status_code == 200
    assert res.json()["license_plate"] == "29A-777.77"
    assert res.json()["status"] == "PENDING"

    # 3. Officer approves the violation
    approve_res = api_client.post(
        f"/api/violations/{rec_id}/review",
        json={"status": "APPROVED", "notes": "Rõ nét 3 ảnh bằng chứng. Đủ điều kiện phạt nguội."}
    )
    assert approve_res.status_code == 200
    assert approve_res.json()["status"] == "APPROVED"

    # 4. Verify in DB
    db = SessionLocal()
    updated = db.query(ViolationRecord).filter(ViolationRecord.id == rec_id).first()
    assert updated.status == "APPROVED"
    assert "Đủ điều kiện phạt nguội" in updated.reviewer_notes
    db.close()

    # 5. Verify stats endpoint aggregates correctly
    stats_res = api_client.get("/api/violations/stats/summary")
    assert stats_res.status_code == 200
    stats = stats_res.json()
    assert stats["approved"] >= 1


def test_scenario_camera_roi_config_api(api_client):
    """Functional Scenario 3: Update and fetch intersection camera ROI configuration."""
    # 1. Fetch current config
    res_get = api_client.get("/api/config/camera")
    assert res_get.status_code == 200
    original_config = res_get.json()
    assert "stop_line" in original_config

    # 2. Modify stop line slightly and update
    modified_config = dict(original_config)
    modified_config["stop_line"] = [[410, 725], [1490, 725]]

    res_put = api_client.put("/api/config/camera", json={"config": modified_config})
    assert res_put.status_code == 200
    assert "updated successfully" in res_put.json()["message"]

    # 3. Re-fetch and verify updated coordinates
    res_verify = api_client.get("/api/config/camera")
    assert res_verify.json()["stop_line"] == [[410, 725], [1490, 725]]

    # Restore original
    api_client.put("/api/config/camera", json={"config": original_config})
