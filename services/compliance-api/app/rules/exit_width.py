from typing import Any

from app.rules.base import RegulationClauseLookup, Rule, RuleResult, register_rule

REGULATION_CLAUSE_SECTION = "3.4.7.2"


class ExitWidthRule(Rule):
    rule_id = "exit-min-width"

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
        exits = project_data.get("exits", [])
        results: list[RuleResult] = []

        for exit_item in exits:
            if isinstance(exit_item, dict):
                exit_id = exit_item["id"]
                clear_width = exit_item["clear_width"]
            else:
                exit_id = exit_item.id
                clear_width = exit_item.clear_width

            passed = clear_width >= minimum_mm
            if passed:
                message = (
                    f"Exit {exit_id} clear width {clear_width}mm meets the "
                    f"minimum of {minimum_mm}mm."
                )
            else:
                message = (
                    f"Exit {exit_id} clear width {clear_width}mm is below the "
                    f"minimum of {minimum_mm}mm."
                )

            results.append(
                RuleResult(
                    rule_id=self.rule_id,
                    passed=passed,
                    message=message,
                    regulation_clause_id=clause.id,
                    evidence={
                        "exit_id": exit_id,
                        "clear_width_mm": clear_width,
                        "minimum_mm": minimum_mm,
                        "regulation_clause_section": REGULATION_CLAUSE_SECTION,
                    },
                )
            )

        return results


# Retained for seed_regulations.py reference values.
MIN_EXIT_CLEAR_WIDTH_MM = 1200.0

exit_width_rule = register_rule(ExitWidthRule())
