from typing import Any

from app.rules.base import Rule, RuleResult, register_rule

MIN_DOOR_CLEAR_WIDTH_MM = 860.0


class DoorWidthRule(Rule):
    rule_id = "door-min-width"

    def evaluate(self, project_data: Any) -> list[RuleResult]:
        doors = project_data.get("doors", [])
        results: list[RuleResult] = []

        for door in doors:
            if isinstance(door, dict):
                door_id = door["id"]
                clear_width = door["clear_width"]
            else:
                door_id = door.id
                clear_width = door.clear_width

            passed = clear_width >= MIN_DOOR_CLEAR_WIDTH_MM
            if passed:
                message = (
                    f"Door {door_id} clear width {clear_width}mm meets the "
                    f"minimum of {MIN_DOOR_CLEAR_WIDTH_MM}mm."
                )
            else:
                message = (
                    f"Door {door_id} clear width {clear_width}mm is below the "
                    f"minimum of {MIN_DOOR_CLEAR_WIDTH_MM}mm."
                )

            results.append(
                RuleResult(
                    rule_id=self.rule_id,
                    passed=passed,
                    message=message,
                    evidence={
                        "door_id": door_id,
                        "clear_width_mm": clear_width,
                        "minimum_mm": MIN_DOOR_CLEAR_WIDTH_MM,
                    },
                )
            )

        return results


door_width_rule = register_rule(DoorWidthRule())
