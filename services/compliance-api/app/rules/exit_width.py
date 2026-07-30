from typing import Any

from app.rules.base import RegulationClauseLookup, Rule, RuleResult, register_rule

MIN_EXIT_CLEAR_WIDTH_MM = 1200.0


class ExitWidthRule(Rule):
    rule_id = "exit-min-width"

    def evaluate(
        self,
        project_data: Any,
        lookup_regulation_clause: RegulationClauseLookup,
    ) -> list[RuleResult]:
        exits = project_data.get("exits", [])
        results: list[RuleResult] = []

        for exit_item in exits:
            if isinstance(exit_item, dict):
                exit_id = exit_item["id"]
                clear_width = exit_item["clear_width"]
            else:
                exit_id = exit_item.id
                clear_width = exit_item.clear_width

            passed = clear_width >= MIN_EXIT_CLEAR_WIDTH_MM
            if passed:
                message = (
                    f"Exit {exit_id} clear width {clear_width}mm meets the "
                    f"minimum of {MIN_EXIT_CLEAR_WIDTH_MM}mm."
                )
            else:
                message = (
                    f"Exit {exit_id} clear width {clear_width}mm is below the "
                    f"minimum of {MIN_EXIT_CLEAR_WIDTH_MM}mm."
                )

            results.append(
                RuleResult(
                    rule_id=self.rule_id,
                    passed=passed,
                    message=message,
                    evidence={
                        "exit_id": exit_id,
                        "clear_width_mm": clear_width,
                        "minimum_mm": MIN_EXIT_CLEAR_WIDTH_MM,
                    },
                )
            )

        return results


exit_width_rule = register_rule(ExitWidthRule())
