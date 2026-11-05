"""Model Training & Fine-Tuning Pipeline for Traffic Violations."""

from .train_detector import train_vehicle_detector
from .train_plate import train_plate_detector

__all__ = [
    "train_vehicle_detector",
    "train_plate_detector",
]
