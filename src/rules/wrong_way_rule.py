"""Wrong-Way Driving Detection Rule."""

import time
import uuid
from typing import List, Dict, Any, Tuple
import numpy as np
from shapely.geometry import Point, Polygon

from .base_rule import BaseViolationRule, ViolationEvent, ViolationType


class WrongWayRule(BaseViolationRule):
    """Detects vehicles traveling in reverse or against the authorized lane flow vector."""

    def __init__(
        self,
        lanes: List[Dict[str, Any]],
        cosine_threshold: float = -0.70, # cos(theta) < -0.70 => theta > 135 deg
        min_continuous_frames: int = 10,
        min_movement_px: float = 30.0,
        enabled: bool = True
    ):
        super().__init__(name="WrongWayRule", enabled=enabled)
        self.lanes = []
        for lane in lanes:
            poly = Polygon(lane["polygon"])
            vec = np.array(lane["flow_vector"], dtype=np.float32)
            norm = np.linalg.norm(vec)
            flow_norm = vec / norm if norm > 1e-4 else np.array([0.0, 1.0])
            self.lanes.append({
                "lane_id": lane.get("lane_id", 0),
                "name": lane.get("name", "Unknown Lane"),
                "polygon": poly,
                "flow_vector": flow_norm
            })

        self.cosine_threshold = cosine_threshold
        self.min_continuous_frames = min_continuous_frames
        self.min_movement_px = min_movement_px

        # track_id -> count of consecutive wrong-way frames
        self._counter: Dict[int, int] = {}

    def evaluate(
        self,
        tracked_vehicles: list,
        context: Dict[str, Any],
        frame_idx: int
    ) -> List[ViolationEvent]:
        if not self.enabled:
            return []

        violations: List[ViolationEvent] = []

        for vehicle in tracked_vehicles:
            tid = vehicle.track_id
            if self.is_recently_flagged(tid):
                continue

            if len(vehicle.trajectory) < self.min_continuous_frames:
                continue

            curr_pos = Point(vehicle.current_position)

            # 1. Identify which lane the vehicle currently occupies
            matching_lane = None
            for lane in self.lanes:
                if lane["polygon"].contains(curr_pos):
                    matching_lane = lane
                    break

            if matching_lane is None:
                self._counter[tid] = 0
                continue

            # 2. Check if the vehicle has moved sufficiently (eliminate stationary noise)
            disp = vehicle.get_displacement_magnitude(step_back_frames=self.min_continuous_frames)
            if disp < self.min_movement_px:
                continue

            # 3. Calculate cosine similarity between vehicle velocity and allowed lane vector
            vx, vy = vehicle.get_velocity_vector(step_back_frames=self.min_continuous_frames)
            veh_vec = np.array([vx, vy], dtype=np.float32)

            lane_vec = matching_lane["flow_vector"]
            cos_theta = float(np.dot(veh_vec, lane_vec))

            # 4. Evaluate against threshold
            if cos_theta < self.cosine_threshold:
                self._counter[tid] = self._counter.get(tid, 0) + 1

                if self._counter[tid] >= self.min_continuous_frames:
                    self.mark_flagged(tid)
                    self._counter[tid] = 0
                    violations.append(
                        ViolationEvent(
                            event_id=f"VIO-WWD-{uuid.uuid4().hex[:8].upper()}",
                            track_id=tid,
                            violation_type=ViolationType.WRONG_WAY,
                            timestamp=time.time(),
                            frame_idx=frame_idx,
                            confidence=vehicle.confidence,
                            vehicle_type=vehicle.class_name,
                            bbox=vehicle.current_bbox,
                            license_plate=vehicle.license_plate,
                            plate_confidence=vehicle.plate_confidence,
                            details={
                                "lane_id": matching_lane["lane_id"],
                                "lane_name": matching_lane["name"],
                                "cos_theta": round(cos_theta, 3),
                                "displacement_px": round(disp, 1),
                            }
                        )
                    )
            else:
                self._counter[tid] = max(0, self._counter.get(tid, 0) - 1)

        return violations
