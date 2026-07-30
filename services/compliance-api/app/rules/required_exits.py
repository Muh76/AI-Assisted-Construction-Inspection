from typing import Any

from app.rules.base import Rule, RuleResult, register_rule

OCCUPANT_LOAD_EXIT_THRESHOLD = 60
MIN_EXITS_ABOVE_THRESHOLD = 2
MIN_EXITS_AT_OR_BELOW_THRESHOLD = 1


class RequiredExitsRule(Rule):
    rule_id = "required-exits"

    def evaluate(self, project_data: Any) -> list[RuleResult]:
        rooms = project_data.get("rooms", [])
        exits = project_data.get("exits", [])

        total_occupant_load = 0
        for room in rooms:
            if isinstance(room, dict):
                total_occupant_load += room["occupant_load"]
            else:
                total_occupant_load += room.occupant_load

        exit_count = len(exits)
        if total_occupant_load > OCCUPANT_LOAD_EXIT_THRESHOLD:
            required_exits = MIN_EXITS_ABOVE_THRESHOLD
        else:
            required_exits = MIN_EXITS_AT_OR_BELOW_THRESHOLD

        passed = exit_count >= required_exits
        if passed:
            message = (
                f"Project has {exit_count} exit(s), meeting the requirement of "
                f"{required_exits} for a total occupant load of {total_occupant_load}."
            )
        else:
            message = (
                f"Project has {exit_count} exit(s), but requires at least "
                f"{required_exits} for a total occupant load of {total_occupant_load}."
            )

        return [
            RuleResult(
                rule_id=self.rule_id,
                passed=passed,
                message=message,
                evidence={
                    "total_occupant_load": total_occupant_load,
                    "exit_count": exit_count,
                    "required_exits": required_exits,
                    "occupant_threshold": OCCUPANT_LOAD_EXIT_THRESHOLD,
                },
            )
        ]


required_exits_rule = register_rule(RequiredExitsRule())
