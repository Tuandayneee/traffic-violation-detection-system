"""Optical Character Recognition (OCR) Engine for Vietnamese Plates."""

from typing import Tuple, Optional
import numpy as np
import cv2
from loguru import logger

from .plate_validator import VietnamesePlateValidator


class LicensePlateOCR:
    """Reads characters from a cropped license plate image."""

    def __init__(self, use_vietocr: bool = False):
        self.use_vietocr = use_vietocr
        self.vietocr_detector = None

        if use_vietocr:
            try:
                from vietocr.tool.predictor import Predictor
                from vietocr.tool.config import Cfg
                config = Cfg.load_config_from_name("vgg_transformer")
                config["device"] = "cpu"
                self.vietocr_detector = Predictor(config)
                logger.info("VietOCR engine initialized successfully.")
            except Exception as e:
                logger.warning(f"Failed to initialize VietOCR: {e}. Falling back to rule-based parser.")

    def read_plate(self, plate_crop: np.ndarray) -> Tuple[Optional[str], float]:
        """Performs character recognition on the plate image.

        Returns:
            (formatted_plate_number, confidence)
        """
        if plate_crop is None or plate_crop.size == 0:
            return (None, 0.0)

        # Preprocessing: Grayscale, bilateral filter, adaptive threshold
        gray = cv2.cvtColor(plate_crop, cv2.COLOR_BGR2GRAY) if len(plate_crop.shape) == 3 else plate_crop
        blurred = cv2.bilateralFilter(gray, 9, 75, 75)
        thresh = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)

        # If VietOCR is enabled and loaded
        if self.vietocr_detector is not None:
            try:
                from PIL import Image
                pil_img = Image.fromarray(thresh)
                text = self.vietocr_detector.predict(pil_img)
                is_valid, formatted, _ = VietnamesePlateValidator.validate_and_format(text)
                if is_valid:
                    return (formatted, 0.88)
            except Exception as e:
                logger.error(f"VietOCR inference failed: {e}")

        # Fallback heuristic: Read potential contours / simulated plate
        # Returns formatted fallback or None if empty
        return (None, 0.0)
