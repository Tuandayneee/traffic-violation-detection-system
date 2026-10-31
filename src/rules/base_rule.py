"""Abstract Base Class and Data Models for Traffic Violation Rules."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional, Tuple
import time


class ViolationType(str, Enum):
    RED_LIGHT = "RED_LIGHT_RUNNING"
    WRONG_WAY = "WRONG_WAY_DRIVING"
    ILLEGAL_TURN = "ILLEGAL_TURN"
    LANE_NON_COMPLIANCE = "LANE_NON_COMPLIANCE"


@dataclass
class ViolationEvent:
    """Encapsulates all metadata for a detected traffic violation."""
    event_id: str
    track_id: int
    violation_type: ViolationType
    timestamp: float
    frame_idx: int
    confidence: float
    vehicle_type: str
    bbox: Tuple[int, int, int, int]
    license_plate: Optional[str] = None
    plate_confidence: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)


class BaseViolationRule(ABC):
    """Interface for modular violation detection rules."""

    def __init__(self, name: str, enabled: bool = True):
        self.name = name
        self.enabled = enabled
        self._flagged_track_ids: Dict[int, float] = {} # track_id -> timestamp

    def is_recently_flagged(self, track_id: int, cooldown_seconds: float = 10.0) -> bool:
        """Prevents duplicate spam alerts for the same vehicle."""
        if track_id in self._flagged_track_ids:
            if time.time() - self._flagged_track_ids[track_id] < cooldown_seconds:
                return True
        return False

    def mark_flagged(self, track_id: int):
        """Marks a track_id as flagged to enforce cooldown."""
        self._flagged_track_ids[track_id] = time.time()

    @abstractmethod
    def evaluate(
        self,
        tracked_vehicles: list,
        context: Dict[str, Any],
        frame_idx: int
    ) -> List[ViolationEvent]:
        """Evaluates active vehicles in the current frame for rule violations."""
        pass
