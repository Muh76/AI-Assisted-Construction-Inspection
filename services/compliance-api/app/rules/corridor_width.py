from typing import Any

from app.rules.base import Rule, RuleResult, register_rule

MIN_CORRIDOR_CLEAR_WIDTH_MM = 1100.0


class CorridorWidthRule(Rule):
    rule_id = "corridor-min-width"

    def evaluate(self, project_data: Any) -> list[RuleResult]:
        corridors = project_data.get("corridors", [])
        results: list[RuleResult] = []

        for corridor in corridors:
            if isinstance(corridor, dict):
                corridor_id = corridor["id"]
                clear_width = corridor["clear_width"]
            else:
                corridor_id = corridor.id
                clear_width = corridor.clear_width

            passed = clear_width >= MIN_CORRIDOR_CLEAR_WIDTH_MM
            if passed:
                message = (
                    f"Corridor {corridor_id} clear width {clear_width}mm meets the "
                    f"minimum of {MIN_CORRIDOR_CLEAR_WIDTH_MM}mm."
                )
            else:
                message = (
                    f"Corridor {corridor_id} clear width {clear_width}mm is below the "
                    f"minimum of {MIN_CORRIDOR_CLEAR_WIDTH_MM}mm."
                )

            results.append(
                RuleResult(
                    rule_id=self.rule_id,
                    passed=passed,
                    message=message,
                    evidence={
                        "corridor_id": corridor_id,
                        "clear_width_mm": clear_width,
                        "minimum_mm": MIN_CORRIDOR_CLEAR_WIDTH_MM,
                    },
                )
            )

        return results


corridor_width_rule = register_rule(CorridorWidthRule())
