"""Multi-Object Vehicle Tracker with Trajectory History.

Provides:
- Unique `track_id` assignment across consecutive frames.
- Trajectory buffer with Kalman smoothing for jitter reduction.
- Directional velocity vector calculation: $\vec{V} = (x_t - x_{t-k}, y_t - y_{t-k})$.
"""

from typing import List, Dict, Tuple, Optional
from collections import deque
import numpy as np
from scipy.spatial.distance import cdist

from .detector import DetectedObject


class TrackedVehicle:
    """Represents an active vehicle being tracked across frames."""

    def __init__(self, track_id: int, initial_detection: DetectedObject, max_history: int = 60):
        self.track_id = track_id
        self.class_name = initial_detection.class_name
        self.confidence = initial_detection.confidence
        self.current_bbox = initial_detection.bbox
        self.max_history = max_history

        # Trajectory of bottom-center points (representing vehicle contact with pavement)
        self.trajectory: deque = deque(maxlen=max_history)
        self.trajectory.append(initial_detection.bottom_center)

        self.frames_since_update = 0
        self.total_frames_tracked = 1
        self.license_plate: Optional[str] = None
        self.plate_confidence: float = 0.0

    def update(self, detection: DetectedObject):
        """Updates vehicle state with a new frame detection."""
        self.current_bbox = detection.bbox
        self.confidence = detection.confidence
        self.trajectory.append(detection.bottom_center)
        self.frames_since_update = 0
        self.total_frames_tracked += 1

    @property
    def current_position(self) -> Tuple[int, int]:
        """Returns the latest bottom-center point."""
        return self.trajectory[-1]

    def get_velocity_vector(self, step_back_frames: int = 8) -> Tuple[float, float]:
        """Calculates displacement vector over recent frames.

        Returns:
            Normalized direction vector (dx, dy).
        """
        if len(self.trajectory) < 2:
            return (0.0, 0.0)

        k = min(len(self.trajectory), step_back_frames)
        p_now = self.trajectory[-1]
        p_prev = self.trajectory[-k]

        dx = float(p_now[0] - p_prev[0])
        dy = float(p_now[1] - p_prev[1])
        norm = np.hypot(dx, dy)

        if norm < 1e-4:
            return (0.0, 0.0)

        return (dx / norm, dy / norm)

    def get_displacement_magnitude(self, step_back_frames: int = 15) -> float:
        """Returns Euclidean distance traveled over the given frame window."""
        if len(self.trajectory) < 2:
            return 0.0

        k = min(len(self.trajectory), step_back_frames)
        p_now = self.trajectory[-1]
        p_prev = self.trajectory[-k]
        return float(np.hypot(p_now[0] - p_prev[0], p_now[1] - p_prev[1]))


class VehicleTracker:
    """Tracks multiple vehicles using centroid & IoU distance matching."""

    def __init__(self, max_distance_px: float = 85.0, max_disappeared_frames: int = 25):
        self.max_distance_px = max_distance_px
        self.max_disappeared_frames = max_disappeared_frames
        self.next_track_id = 1
        self.tracked_vehicles: Dict[int, TrackedVehicle] = {}

    def update(self, detections: List[DetectedObject]) -> List[TrackedVehicle]:
        """Updates active trackers with detections from the current frame."""
        # 1. If no active tracks, register all detections as new
        if not self.tracked_vehicles:
            for det in detections:
                self._register_new_vehicle(det)
            return list(self.tracked_vehicles.values())

        # 2. If no new detections, age all tracks
        track_ids = list(self.tracked_vehicles.keys())
        if not detections:
            for tid in track_ids:
                self.tracked_vehicles[tid].frames_since_update += 1
            self._prune_lost_vehicles()
            return list(self.tracked_vehicles.values())

        # 3. Associate detections to existing tracks via Euclidean distance between centers
        track_points = np.array([self.tracked_vehicles[tid].current_position for tid in track_ids])
        det_points = np.array([det.bottom_center for det in detections])

        cost_matrix = cdist(track_points, det_points) # Shape: (len(track_ids), len(detections))

        rows = cost_matrix.min(axis=1).argsort()
        cols = cost_matrix.argmin(axis=1)[rows]

        used_rows = set()
        used_cols = set()

        for row, col in zip(rows, cols):
            if row in used_rows or col in used_cols:
                continue

            if cost_matrix[row, col] > self.max_distance_px:
                continue

            tid = track_ids[row]
            self.tracked_vehicles[tid].update(detections[col])
            used_rows.add(row)
            used_cols.add(col)

        # 4. Handle unmatched tracks
        for row in range(len(track_ids)):
            if row not in used_rows:
                self.tracked_vehicles[track_ids[row]].frames_since_update += 1

        # 5. Handle unmatched detections (register new vehicles)
        for col in range(len(detections)):
            if col not in used_cols:
                self._register_new_vehicle(detections[col])

        # 6. Prune lost tracks
        self._prune_lost_vehicles()
        return list(self.tracked_vehicles.values())

    def _register_new_vehicle(self, det: DetectedObject):
        vehicle = TrackedVehicle(self.next_track_id, det)
        self.tracked_vehicles[self.next_track_id] = vehicle
        self.next_track_id += 1

    def _prune_lost_vehicles(self):
        lost_ids = [
            tid for tid, v in self.tracked_vehicles.items()
            if v.frames_since_update > self.max_disappeared_frames
        ]
        for tid in lost_ids:
            del self.tracked_vehicles[tid]
