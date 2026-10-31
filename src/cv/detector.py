"""Vehicle Detector Wrapper for YOLOv8/v11 Models."""

from dataclasses import dataclass
from typing import List, Tuple, Optional
import numpy as np
from loguru import logger

try:
    from ultralytics import YOLO
    ULTRALYTICS_AVAILABLE = True
except ImportError:
    ULTRALYTICS_AVAILABLE = False


@dataclass
class DetectedObject:
    """Represents a detected object in a single frame."""
    bbox: Tuple[int, int, int, int] # (x1, y1, x2, y2) in pixel space
    confidence: float
    class_id: int
    class_name: str

    @property
    def bottom_center(self) -> Tuple[int, int]:
        """Returns the bottom-center contact point with the pavement."""
        x1, y1, x2, y2 = self.bbox
        return ((x1 + x2) // 2, y2)

    @property
    def centroid(self) -> Tuple[int, int]:
        """Returns the center point of the bounding box."""
        x1, y1, x2, y2 = self.bbox
        return ((x1 + x2) // 2, (y1 + y2) // 2)


class VehicleDetector:
    """Wraps Ultralytics YOLO to filter and return standard vehicle classes."""

    # COCO Class mapping for relevant vehicles
    COCO_VEHICLE_MAP = {
        2: "car",
        3: "motorcycle",
        5: "bus",
        7: "truck",
    }

    def __init__(
        self,
        model_path: str = "yolov8n.pt",
        conf_thresh: float = 0.45,
        iou_thresh: float = 0.50,
        device: str = "cpu"
    ):
        self.conf_thresh = conf_thresh
        self.iou_thresh = iou_thresh
        self.device = device
        self.model = None

        if ULTRALYTICS_AVAILABLE:
            try:
                self.model = YOLO(model_path)
                logger.info(f"Loaded YOLO vehicle detector from {model_path} on {device}")
            except Exception as e:
                logger.warning(f"Could not load weights {model_path}: {e}. Running in standby mode.")

    def detect(self, frame: np.ndarray) -> List[DetectedObject]:
        """Performs inference and returns detected vehicles."""
        if self.model is None:
            return []

        results = self.model.predict(
            source=frame,
            conf=self.conf_thresh,
            iou=self.iou_thresh,
            device=self.device,
            verbose=False
        )

        detections: List[DetectedObject] = []
        if not results:
            return detections

        r = results[0]
        boxes = r.boxes.xyxy.cpu().numpy()
        confs = r.boxes.conf.cpu().numpy()
        classes = r.boxes.cls.cpu().numpy().astype(int)

        for box, conf, cls_id in zip(boxes, confs, classes):
            # Only keep vehicle classes
            if cls_id in self.COCO_VEHICLE_MAP:
                cname = self.COCO_VEHICLE_MAP[cls_id]
                x1, y1, x2, y2 = map(int, box)
                detections.append(
                    DetectedObject(
                        bbox=(x1, y1, x2, y2),
                        confidence=float(conf),
                        class_id=cls_id,
                        class_name=cname
                    )
                )

        return detections
