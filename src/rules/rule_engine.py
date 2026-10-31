"""Traffic Rule Engine Coordinator."""

from typing import List, Dict, Any
from .base_rule import BaseViolationRule, ViolationEvent


class TrafficRuleEngine:
    """Manages and executes all active violation rules across frames."""

    def __init__(self, rules: List[BaseViolationRule] = None):
        self.rules: List[BaseViolationRule] = rules or []

    def add_rule(self, rule: BaseViolationRule):
        self.rules.append(rule)

    def process_frame(
        self,
        tracked_vehicles: list,
        context: Dict[str, Any],
        frame_idx: int
    ) -> List[ViolationEvent]:
        """Applies all active rules to the current frame context."""
        all_violations: List[ViolationEvent] = []

        for rule in self.rules:
            if rule.enabled:
                violations = rule.evaluate(tracked_vehicles, context, frame_idx)
                if violations:
                    all_violations.extend(violations)

        return all_violations
