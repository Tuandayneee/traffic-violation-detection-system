"""Traffic Light ROI State Classifier.

Classifies the active state of a traffic light (RED, YELLOW, GREEN, UNKNOWN)
using HSV color segmentation and spatial brightness distribution.
Includes temporal smoothing to eliminate frame flicker.
"""

from enum import Enum
from typing import Tuple, List, Optional
import numpy as np
import cv2
from loguru import logger


class TrafficLightState(str, Enum):
    RED = "RED"
    YELLOW = "YELLOW"
    GREEN = "GREEN"
    UNKNOWN = "UNKNOWN"


class TrafficLightClassifier:
    """Analyzes a cropped traffic light region to determine active signal state."""

    def __init__(self, history_size: int = 5):
        self.history_size = history_size
        self._history: List[TrafficLightState] = []

    def classify_roi(self, light_crop: np.ndarray) -> TrafficLightState:
        """Classifies a traffic light image crop into RED, YELLOW, or GREEN."""
        if light_crop is None or light_crop.size == 0:
            return TrafficLightState.UNKNOWN

        hsv = cv2.cvtColor(light_crop, cv2.COLOR_BGR2HSV)
        h, s, v = cv2.split(hsv)

        # 1. Color range masks in HSV
        # Red spans 0-10 and 160-180 in hue
        red_mask1 = cv2.inRange(hsv, np.array([0, 100, 100]), np.array([10, 255, 255]))
        red_mask2 = cv2.inRange(hsv, np.array([160, 100, 100]), np.array([180, 255, 255]))
        red_mask = cv2.bitwise_or(red_mask1, red_mask2)

        # Yellow spans 15-35
        yellow_mask = cv2.inRange(hsv, np.array([15, 100, 100]), np.array([35, 255, 255]))

        # Green spans 40-90
        green_mask = cv2.inRange(hsv, np.array([40, 100, 100]), np.array([90, 255, 255]))

        red_pixels = cv2.countNonZero(red_mask)
        yellow_pixels = cv2.countNonZero(yellow_mask)
        green_pixels = cv2.countNonZero(green_mask)

        # Determine dominant color with minimum threshold
        min_pixels = max(10, int(light_crop.shape[0] * light_crop.shape[1] * 0.02))

        counts = {
            TrafficLightState.RED: red_pixels,
            TrafficLightState.YELLOW: yellow_pixels,
            TrafficLightState.GREEN: green_pixels
        }

        dominant_state = max(counts, key=counts.get)
        if counts[dominant_state] < min_pixels:
            raw_state = TrafficLightState.UNKNOWN
        else:
            raw_state = dominant_state

        # Temporal smoothing to prevent single-frame flickering
        self._history.append(raw_state)
        if len(self._history) > self.history_size:
            self._history.pop(0)

        # Majority vote
        valid_votes = [s for s in self._history if s != TrafficLightState.UNKNOWN]
        if not valid_votes:
            return TrafficLightState.UNKNOWN

        return max(set(valid_votes), key=valid_votes.count)
