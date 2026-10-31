"""Synthetic Data Generator for CI/CD Testing & Simulation.

Generates realistic mock frames containing:
- Asphalt road with stop line and lane markings.
- Moving vehicle bounding boxes with persistent IDs.
- Simulated traffic light states (Red, Yellow, Green).
- Vietnamese-style license plates on vehicles.
"""

from pathlib import Path
from typing import Tuple, List, Dict, Any
import numpy as np
import cv2


class SyntheticTrafficGenerator:
    """Generates synthetic video sequences with ground-truth traffic events."""

    def __init__(self, width: int = 1920, height: int = 1080):
        self.width = width
        self.height = height

    def generate_base_intersection_frame(self, traffic_light_state: str = "GREEN") -> np.ndarray:
        """Renders an intersection road background with markings and traffic light."""
        # 1. Dark asphalt background
        frame = np.full((self.height, self.width, 3), 45, dtype=np.uint8)

        # 2. Road surface polygon
        road_pts = np.array([[300, 700], [1620, 700], [1820, 1080], [100, 1080]], np.int32)
        cv2.fillPoly(frame, [road_pts], (60, 60, 60))

        # 3. White Stop Line
        cv2.line(frame, (400, 720), (1520, 720), (255, 255, 255), 10)

        # 4. Lane divider dashed lines
        cv2.line(frame, (750, 720), (600, 1080), (255, 255, 255), 4)
        cv2.line(frame, (1120, 720), (1180, 1080), (255, 255, 255), 4)

        # 5. Traffic Light Housing on the right (ROI: [1450, 80, 1530, 260])
        cv2.rectangle(frame, (1450, 80), (1530, 260), (20, 20, 20), -1)
        cv2.rectangle(frame, (1450, 80), (1530, 260), (180, 180, 180), 2)

        # Circles for Red, Yellow, Green
        red_color = (0, 0, 255) if traffic_light_state.upper() == "RED" else (0, 0, 60)
        yellow_color = (0, 220, 255) if traffic_light_state.upper() == "YELLOW" else (0, 60, 60)
        green_color = (0, 255, 0) if traffic_light_state.upper() == "GREEN" else (0, 60, 0)

        cv2.circle(frame, (1490, 115), 22, red_color, -1)
        cv2.circle(frame, (1490, 170), 22, yellow_color, -1)
        cv2.circle(frame, (1490, 225), 22, green_color, -1)

        return frame

    def render_vehicle(
        self,
        frame: np.ndarray,
        bbox: Tuple[int, int, int, int],
        vehicle_type: str = "car",
        plate_text: str = "29A-888.88"
    ) -> np.ndarray:
        """Renders a simulated vehicle with headlights and a license plate."""
        x1, y1, x2, y2 = bbox
        color = (180, 100, 40) if vehicle_type == "car" else (40, 180, 100)

        # Vehicle Body
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, -1)
        cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 255, 255), 2)

        # License Plate (White background with black text)
        pw, ph = int((x2 - x1) * 0.45), int((y2 - y1) * 0.20)
        px1 = x1 + (x2 - x1 - pw) // 2
        py1 = y2 - ph - 6
        px2, py2 = px1 + pw, py1 + ph

        cv2.rectangle(frame, (px1, py1), (px2, py2), (240, 240, 240), -1)
        cv2.rectangle(frame, (px1, py1), (px2, py2), (10, 10, 10), 1)

        font_scale = 0.4
        cv2.putText(frame, plate_text, (px1 + 4, py1 + ph - 4), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 0, 0), 1)

        return frame
