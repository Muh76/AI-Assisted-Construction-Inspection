from typing import Any

from app.models import FireProtectionItemType
from app.rules.base import RegulationClauseLookup, Rule, RuleResult, register_rule

MAX_FIRE_EXTINGUISHER_TRAVEL_DISTANCE_M = 23.0


class FireExtinguisherRule(Rule):
    rule_id = "fire-extinguisher-travel-distance"

    def evaluate(
        self,
        project_data: Any,
        lookup_regulation_clause: RegulationClauseLookup,
    ) -> list[RuleResult]:
        items = project_data.get("fire_protection_items", [])
        results: list[RuleResult] = []

        for item in items:
            if isinstance(item, dict):
                item_type = item["item_type"]
                item_id = item["id"]
                location = item.get("location", str(item_id))
                travel_distance = item.get("travel_distance_to_nearest")
            else:
                item_type = item.item_type
                item_id = item.id
                location = item.location
                travel_distance = item.travel_distance_to_nearest

            if isinstance(item_type, FireProtectionItemType):
                item_type_value = item_type.value
            else:
                item_type_value = str(item_type)

            if item_type_value != FireProtectionItemType.FIRE_EXTINGUISHER.value:
                continue

            if travel_distance is None:
                passed = False
                message = (
                    f"Fire extinguisher {item_id} ({location}) has no travel distance "
                    f"to nearest recorded."
                )
            elif travel_distance <= MAX_FIRE_EXTINGUISHER_TRAVEL_DISTANCE_M:
                passed = True
                message = (
                    f"Fire extinguisher {item_id} ({location}) travel distance "
                    f"{travel_distance}m is within the maximum of "
                    f"{MAX_FIRE_EXTINGUISHER_TRAVEL_DISTANCE_M}m."
                )
            else:
                passed = False
                message = (
                    f"Fire extinguisher {item_id} ({location}) travel distance "
                    f"{travel_distance}m exceeds the maximum of "
                    f"{MAX_FIRE_EXTINGUISHER_TRAVEL_DISTANCE_M}m."
                )

            results.append(
                RuleResult(
                    rule_id=self.rule_id,
                    passed=passed,
                    message=message,
                    evidence={
                        "fire_protection_item_id": item_id,
                        "item_type": item_type_value,
                        "travel_distance_to_nearest_m": travel_distance,
                        "maximum_m": MAX_FIRE_EXTINGUISHER_TRAVEL_DISTANCE_M,
                    },
                )
            )

        return results


fire_extinguisher_rule = register_rule(FireExtinguisherRule())
