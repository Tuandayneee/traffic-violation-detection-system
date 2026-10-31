"""Unit Tests for Module 2: Core CV, Tracking & ALPR."""

import numpy as np
import pytest

from src.cv.traffic_light import TrafficLightClassifier, TrafficLightState
from src.cv.detector import DetectedObject
from src.cv.tracker import VehicleTracker
from src.cv.alpr.plate_validator import VietnamesePlateValidator


def test_traffic_light_classifier_red():
    """Verify red light crop classification."""
    classifier = TrafficLightClassifier(history_size=3)

    # Create solid red crop
    red_crop = np.zeros((60, 60, 3), dtype=np.uint8)
    red_crop[:, :] = (0, 0, 255) # BGR Red

    state = classifier.classify_roi(red_crop)
    assert state == TrafficLightState.RED


def test_vehicle_tracker_persistence():
    """Verify that tracker persists track_id and builds trajectory."""
    tracker = VehicleTracker(max_distance_px=100.0)

    # Frame 1: Detection at (100, 200)
    det1 = DetectedObject(bbox=(90, 150, 110, 200), confidence=0.9, class_id=2, class_name="car")
    tracks = tracker.update([det1])
    assert len(tracks) == 1
    tid = tracks[0].track_id

    # Frame 2: Vehicle moved to (105, 230)
    det2 = DetectedObject(bbox=(95, 180, 115, 230), confidence=0.92, class_id=2, class_name="car")
    tracks2 = tracker.update([det2])
    assert len(tracks2) == 1
    assert tracks2[0].track_id == tid
    assert len(tracks2[0].trajectory) == 2

    # Vector should point forward/downward (+y)
    vx, vy = tracks2[0].get_velocity_vector()
    assert vy > 0.0


def test_vietnamese_plate_validator():
    """Verify regex parsing for car and motorbike plates."""
    # Car 5-digit
    valid, formatted, cat = VietnamesePlateValidator.validate_and_format("30A12345")
    assert valid is True
    assert formatted == "30A-123.45"
    assert cat == "CAR"

    # Motorbike
    valid, formatted, cat = VietnamesePlateValidator.validate_and_format("29-B1 67890")
    assert valid is True
    assert formatted == "29-B1 678.90"
    assert cat == "MOTORCYCLE"

    # Invalid
    valid, formatted, cat = VietnamesePlateValidator.validate_and_format("XYZ9999999")
    assert valid is False
