from typing import Any

from app.rules.base import RegulationClauseLookup, Rule, RuleResult, register_rule

REGULATION_CLAUSE_SECTION = "3.2.2.1"


class SprinklerCoverageRule(Rule):
    rule_id = "sprinkler-coverage"

    def evaluate(
        self,
        project_data: Any,
        lookup_regulation_clause: RegulationClauseLookup,
    ) -> list[RuleResult]:
        clause = lookup_regulation_clause(REGULATION_CLAUSE_SECTION)
        if clause is None:
            return [
                RuleResult(
                    rule_id=self.rule_id,
                    passed=False,
                    message=(
                        f"Regulation clause {REGULATION_CLAUSE_SECTION} was not found."
                    ),
                )
            ]

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
                    regulation_clause_id=clause.id,
                    evidence={
                        "room_id": room_id,
                        "sprinklered": sprinklered,
                        "regulation_clause_section": REGULATION_CLAUSE_SECTION,
                    },
                )
            )

        return results


sprinkler_coverage_rule = register_rule(SprinklerCoverageRule())
