"""Red Light Violation Detection Rule."""

import time
import uuid
from typing import List, Dict, Any, Tuple
from shapely.geometry import LineString, Point, Polygon

from .base_rule import BaseViolationRule, ViolationEvent, ViolationType
from ..cv.traffic_light import TrafficLightState


class RedLightRule(BaseViolationRule):
    """Detects vehicles traversing the stop line and advancing into an intersection on RED."""

    def __init__(
        self,
        stop_line: List[List[int]],
        intersection_polygon: List[List[int]],
        min_crossing_depth_px: int = 25,
        enabled: bool = True
    ):
        super().__init__(name="RedLightRule", enabled=enabled)
        self.stop_line_geom = LineString(stop_line)
        self.intersection_geom = Polygon(intersection_polygon)
        self.min_crossing_depth_px = min_crossing_depth_px

    def evaluate(
        self,
        tracked_vehicles: list,
        context: Dict[str, Any],
        frame_idx: int
    ) -> List[ViolationEvent]:
        if not self.enabled:
            return []

        light_state = context.get("traffic_light_state", TrafficLightState.UNKNOWN)
        if light_state != TrafficLightState.RED:
            return []

        violations: List[ViolationEvent] = []

        for vehicle in tracked_vehicles:
            tid = vehicle.track_id
            if self.is_recently_flagged(tid):
                continue

            if len(vehicle.trajectory) < 2:
                continue

            # Check recent trajectory window (up to last 10 points)
            traj_pts = list(vehicle.trajectory)[-min(len(vehicle.trajectory), 10):]
            recent_motion = LineString(traj_pts)

            # 1. Did the vehicle's trajectory intersect the stop line?
            if recent_motion.intersects(self.stop_line_geom):
                p_curr = vehicle.trajectory[-1]
                curr_point = Point(p_curr)

                # 2. Is current position advancing into the intersection conflict zone?
                if self.intersection_geom.contains(curr_point):
                    # 3. Confirm crossing direction & depth threshold
                    dist_from_stop_line = self.stop_line_geom.distance(curr_point)
                    if dist_from_stop_line >= self.min_crossing_depth_px:
                        self.mark_flagged(tid)
                        violations.append(
                            ViolationEvent(
                                event_id=f"VIO-RLR-{uuid.uuid4().hex[:8].upper()}",
                                track_id=tid,
                                violation_type=ViolationType.RED_LIGHT,
                                timestamp=time.time(),
                                frame_idx=frame_idx,
                                confidence=vehicle.confidence,
                                vehicle_type=vehicle.class_name,
                                bbox=vehicle.current_bbox,
                                license_plate=vehicle.license_plate,
                                plate_confidence=vehicle.plate_confidence,
                                details={
                                    "light_state": str(light_state),
                                    "distance_past_line_px": round(dist_from_stop_line, 1),
                                    "speed_vector": vehicle.get_velocity_vector(),
                                }
                            )
                        )

        return violations
