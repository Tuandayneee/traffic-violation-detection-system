"""Automatic License Plate Recognition (ALPR) Subsystem."""

from .plate_validator import VietnamesePlateValidator
from .plate_detector import PlateDetector
from .ocr_engine import LicensePlateOCR

__all__ = [
    "VietnamesePlateValidator",
    "PlateDetector",
    "LicensePlateOCR",
]
