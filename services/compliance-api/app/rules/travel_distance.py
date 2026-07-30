from typing import Any

from app.rules.base import RegulationClauseLookup, Rule, RuleResult, register_rule

REGULATION_CLAUSE_SECTION = "3.4.2.7"


class TravelDistanceRule(Rule):
    rule_id = "travel-distance"

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

        maximum_m = clause.threshold_value
        rooms = project_data.get("rooms", [])
        results: list[RuleResult] = []

        for room in rooms:
            if isinstance(room, dict):
                room_id = room["id"]
                name = room.get("name", str(room_id))
                travel_distance = room["travel_distance"]
            else:
                room_id = room.id
                name = room.name
                travel_distance = room.travel_distance

            passed = travel_distance <= maximum_m
            if passed:
                message = (
                    f"Room {room_id} ({name}) travel distance {travel_distance}m is within "
                    f"the maximum of {maximum_m}m."
                )
            else:
                message = (
                    f"Room {room_id} ({name}) travel distance {travel_distance}m exceeds "
                    f"the maximum of {maximum_m}m."
                )

            results.append(
                RuleResult(
                    rule_id=self.rule_id,
                    passed=passed,
                    message=message,
                    regulation_clause_id=clause.id,
                    evidence={
                        "room_id": room_id,
                        "travel_distance_m": travel_distance,
                        "maximum_m": maximum_m,
                        "regulation_clause_section": REGULATION_CLAUSE_SECTION,
                    },
                )
            )

        return results


# Retained for seed_regulations.py reference values.
MAX_TRAVEL_DISTANCE_SPRINKLERED_M = 45.0

travel_distance_rule = register_rule(TravelDistanceRule())
