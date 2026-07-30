from typing import Any

from app.rules.base import RegulationClauseLookup, Rule, RuleResult, register_rule

# Maximum travel distance in metres (placeholder for sprinklered buildings).
MAX_TRAVEL_DISTANCE_SPRINKLERED_M = 45.0


class TravelDistanceRule(Rule):
    rule_id = "travel-distance"

    def evaluate(
        self,
        project_data: Any,
        lookup_regulation_clause: RegulationClauseLookup,
    ) -> list[RuleResult]:
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

            passed = travel_distance <= MAX_TRAVEL_DISTANCE_SPRINKLERED_M
            if passed:
                message = (
                    f"Room {room_id} ({name}) travel distance {travel_distance}m is within "
                    f"the maximum of {MAX_TRAVEL_DISTANCE_SPRINKLERED_M}m."
                )
            else:
                message = (
                    f"Room {room_id} ({name}) travel distance {travel_distance}m exceeds "
                    f"the maximum of {MAX_TRAVEL_DISTANCE_SPRINKLERED_M}m."
                )

            results.append(
                RuleResult(
                    rule_id=self.rule_id,
                    passed=passed,
                    message=message,
                    evidence={
                        "room_id": room_id,
                        "travel_distance_m": travel_distance,
                        "maximum_m": MAX_TRAVEL_DISTANCE_SPRINKLERED_M,
                    },
                )
            )

        return results


travel_distance_rule = register_rule(TravelDistanceRule())
