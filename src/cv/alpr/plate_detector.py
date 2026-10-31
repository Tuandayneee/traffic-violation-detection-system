"""License Plate Bounding Box Detector."""

from typing import List, Tuple, Optional
import numpy as np
import cv2
from loguru import logger

try:
    from ultralytics import YOLO
    ULTRALYTICS_AVAILABLE = True
except ImportError:
    ULTRALYTICS_AVAILABLE = False


class PlateDetector:
    """Detects rectangular license plate regions within a vehicle crop."""

    def __init__(self, model_path: str = "models/checkpoints/plate_detector.pt", conf_thresh: float = 0.35):
        self.conf_thresh = conf_thresh
        self.model = None

        if ULTRALYTICS_AVAILABLE:
            try:
                self.model = YOLO(model_path)
                logger.info(f"Loaded Plate Detector from {model_path}")
            except Exception as e:
                logger.warning(f"Plate detector checkpoint not found: {e}. Using geometric heuristic fallback.")

    def detect_plates(self, vehicle_crop: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """Detects plates within a cropped vehicle image.

        Returns:
            List of plate bounding boxes [(x1, y1, x2, y2)] relative to vehicle_crop.
        """
        if vehicle_crop is None or vehicle_crop.size == 0:
            return []

        if self.model is not None:
            results = self.model.predict(source=vehicle_crop, conf=self.conf_thresh, verbose=False)
            if results and len(results[0].boxes) > 0:
                boxes = results[0].boxes.xyxy.cpu().numpy()
                return [tuple(map(int, box)) for box in boxes]

        # Heuristic fallback: lower 35% of vehicle crop usually houses the plate
        vh, vw = vehicle_crop.shape[:2]
        pw = int(vw * 0.50)
        ph = int(vh * 0.22)
        px1 = (vw - pw) // 2
        py1 = int(vh * 0.70)
        px2 = px1 + pw
        py2 = min(vh - 2, py1 + ph)

        return [(px1, py1, px2, py2)]
