from typing import Any

from app.rules.base import RegulationClauseLookup, Rule, RuleResult, register_rule

MIN_CORRIDOR_CLEAR_WIDTH_MM = 1100.0
REGULATION_CLAUSE_SECTION = "3.3.2.4"


class CorridorWidthRule(Rule):
    rule_id = "corridor-min-width"

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
        corridors = project_data.get("corridors", [])
        results: list[RuleResult] = []

        for corridor in corridors:
            if isinstance(corridor, dict):
                corridor_id = corridor["id"]
                clear_width = corridor["clear_width"]
            else:
                corridor_id = corridor.id
                clear_width = corridor.clear_width

            passed = clear_width >= minimum_mm
            if passed:
                message = (
                    f"Corridor {corridor_id} clear width {clear_width}mm meets the "
                    f"minimum of {minimum_mm}mm."
                )
            else:
                message = (
                    f"Corridor {corridor_id} clear width {clear_width}mm is below the "
                    f"minimum of {minimum_mm}mm."
                )

            results.append(
                RuleResult(
                    rule_id=self.rule_id,
                    passed=passed,
                    message=message,
                    regulation_clause_id=clause.id,
                    evidence={
                        "corridor_id": corridor_id,
                        "clear_width_mm": clear_width,
                        "minimum_mm": minimum_mm,
                        "regulation_clause_section": REGULATION_CLAUSE_SECTION,
                    },
                )
            )

        return results


corridor_width_rule = register_rule(CorridorWidthRule())
