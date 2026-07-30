from typing import Any

from app.rules.base import RegulationClauseLookup, Rule, RuleResult, register_rule

MIN_DOOR_CLEAR_WIDTH_MM = 860.0
REGULATION_CLAUSE_SECTION = "3.4.7.1"


class DoorWidthRule(Rule):
    rule_id = "door-min-width"

    def evaluate(
        self,
        project_data: Any,
        lookup_regulation_clause: RegulationClauseLookup,
    ) -> list[RuleResult]:
        clause = lookup_regulation_clause(REGULATION_CLAUSE_SECTION)
        if clause is None or clause.threshold_value is None:
            return [
                RuleResult(
                    rule_id=self.rule_id,
                    passed=False,
                    message=(
                        f"Regulation clause {REGULATION_CLAUSE_SECTION} was not found "
                        "or has no threshold value."
                    ),
                    regulation_clause_id=clause.id if clause is not None else None,
                )
            ]

        minimum_mm = clause.threshold_value
        doors = project_data.get("doors", [])
        results: list[RuleResult] = []

        for door in doors:
            if isinstance(door, dict):
                door_id = door["id"]
                clear_width = door["clear_width"]
            else:
                door_id = door.id
                clear_width = door.clear_width

            passed = clear_width >= minimum_mm
            if passed:
                message = (
                    f"Door {door_id} clear width {clear_width}mm meets the "
                    f"minimum of {minimum_mm}mm."
                )
            else:
                message = (
                    f"Door {door_id} clear width {clear_width}mm is below the "
                    f"minimum of {minimum_mm}mm."
                )

            results.append(
                RuleResult(
                    rule_id=self.rule_id,
                    passed=passed,
                    message=message,
                    regulation_clause_id=clause.id,
                    evidence={
                        "door_id": door_id,
                        "clear_width_mm": clear_width,
                        "minimum_mm": minimum_mm,
                        "regulation_clause_section": REGULATION_CLAUSE_SECTION,
                    },
                )
            )

        return results


door_width_rule = register_rule(DoorWidthRule())
