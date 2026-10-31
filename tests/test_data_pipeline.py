"""Unit Tests for Module 1: Data Engineering & Preprocessing."""

import os
from pathlib import Path
import numpy as np
import pytest

from src.data.synthetic_generator import SyntheticTrafficGenerator
from src.data.dataset_validator import DatasetValidator


def test_synthetic_frame_generation():
    """Verify synthetic frame dimensions and visual elements."""
    gen = SyntheticTrafficGenerator(width=1280, height=720)
    frame = gen.generate_base_intersection_frame(traffic_light_state="RED")

    assert frame.shape == (720, 1280, 3)
    assert frame.dtype == np.uint8

    # Render vehicle
    frame_with_car = gen.render_vehicle(frame, bbox=(400, 500, 550, 620), vehicle_type="car", plate_text="30F-123.45")
    assert frame_with_car.shape == (720, 1280, 3)


def test_dataset_validator_empty_dir(tmp_path):
    """Verify validator handles missing and empty directory gracefully."""
    validator = DatasetValidator(str(tmp_path), class_names=["car", "motorcycle", "bus", "truck"])
    stats = validator.validate_split("train")

    assert stats["total_images"] == 0
    assert stats["valid_images"] == 0
