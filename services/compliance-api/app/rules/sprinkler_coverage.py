from typing import Any

from app.rules.base import Rule, RuleResult, register_rule


class SprinklerCoverageRule(Rule):
    rule_id = "sprinkler-coverage"

    def evaluate(self, project_data: Any) -> list[RuleResult]:
        rooms = project_data.get("rooms", [])
        results: list[RuleResult] = []

        for room in rooms:
            if isinstance(room, dict):
                room_id = room["id"]
                name = room.get("name", str(room_id))
                sprinklered = room["sprinklered"]
            else:
                room_id = room.id
                name = room.name
                sprinklered = room.sprinklered

            passed = sprinklered is True
            if passed:
                message = f"Room {room_id} ({name}) is sprinklered."
            else:
                message = f"Room {room_id} ({name}) is not sprinklered."

            results.append(
                RuleResult(
                    rule_id=self.rule_id,
                    passed=passed,
                    message=message,
                    evidence={
                        "room_id": room_id,
                        "sprinklered": sprinklered,
                    },
                )
            )

        return results


sprinkler_coverage_rule = register_rule(SprinklerCoverageRule())
