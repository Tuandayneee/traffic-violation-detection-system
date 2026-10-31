"""Illegal Turn & Lane Non-Compliance Detection Rule."""

import time
import uuid
from typing import List, Dict, Any, Tuple
import numpy as np
from shapely.geometry import Point, Polygon

from .base_rule import BaseViolationRule, ViolationEvent, ViolationType


class IllegalTurnRule(BaseViolationRule):
    """Detects unauthorized turns from lanes designated strictly for other directions."""

    def __init__(
        self,
        lanes: List[Dict[str, Any]],
        min_trajectory_len: int = 12,
        turn_angle_threshold: float = 0.55,
        enabled: bool = True
    ):
        super().__init__(name="IllegalTurnRule", enabled=enabled)
        self.lanes = []
        for lane in lanes:
            poly = Polygon(lane["polygon"])
            self.lanes.append({
                "lane_id": lane.get("lane_id", 0),
                "name": lane.get("name", "Unknown Lane"),
                "polygon": poly,
                "allowed_directions": [d.upper() for d in lane.get("allowed_directions", ["STRAIGHT"])]
            })

        self.min_trajectory_len = min_trajectory_len
        self.turn_angle_threshold = turn_angle_threshold
        # Stores origin lane id for each tracked vehicle: track_id -> lane_dict
        self._origin_lanes: Dict[int, Dict[str, Any]] = {}

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

            # Record origin lane when vehicle first enters the camera scene
            if tid not in self._origin_lanes and len(vehicle.trajectory) >= 3:
                first_pos = Point(vehicle.trajectory[0])
                for lane in self.lanes:
                    if lane["polygon"].contains(first_pos):
                        self._origin_lanes[tid] = lane
                        break

            origin_lane = self._origin_lanes.get(tid)
            if origin_lane is None:
                continue

            if len(vehicle.trajectory) < self.min_trajectory_len:
                continue

            allowed = origin_lane["allowed_directions"]
            vx, vy = vehicle.get_velocity_vector(step_back_frames=self.min_trajectory_len)

            # Check for violation scenarios:
            # 1. Straight-only lane but vehicle makes a sharp turn (vx is large compared to vy)
            is_turning_left = (vx < -self.turn_angle_threshold)
            is_turning_right = (vx > self.turn_angle_threshold)

            has_violated = False
            violation_detail = ""

            if "STRAIGHT" in allowed and "LEFT" not in allowed and is_turning_left:
                has_violated = True
                violation_detail = f"Rẽ trái trái phép từ {origin_lane['name']} (Chỉ cho phép {allowed})"

            elif "STRAIGHT" in allowed and "RIGHT" not in allowed and is_turning_right:
                has_violated = True
                violation_detail = f"Rẽ phải trái phép từ {origin_lane['name']} (Chỉ cho phép {allowed})"

            elif "LEFT" in allowed and "STRAIGHT" not in allowed and not is_turning_left:
                # Started in turn-only lane but continued straight
                if abs(vx) < 0.20 and vy > 0.70:
                    has_violated = True
                    violation_detail = f"Đi thẳng trái phép từ {origin_lane['name']} (Chỉ dành cho rẽ trái)"

            if has_violated:
                self.mark_flagged(tid)
                violations.append(
                    ViolationEvent(
                        event_id=f"VIO-ILT-{uuid.uuid4().hex[:8].upper()}",
                        track_id=tid,
                        violation_type=ViolationType.ILLEGAL_TURN,
                        timestamp=time.time(),
                        frame_idx=frame_idx,
                        confidence=vehicle.confidence,
                        vehicle_type=vehicle.class_name,
                        bbox=vehicle.current_bbox,
                        license_plate=vehicle.license_plate,
                        plate_confidence=vehicle.plate_confidence,
                        details={
                            "lane_id": origin_lane["lane_id"],
                            "lane_name": origin_lane["name"],
                            "allowed": allowed,
                            "motion_vector": (round(vx, 3), round(vy, 3)),
                            "description": violation_detail
                        }
                    )
                )

        return violations
