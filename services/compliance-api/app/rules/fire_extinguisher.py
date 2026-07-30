from typing import Any

from app.models import FireProtectionItemType
from app.rules.base import RegulationClauseLookup, Rule, RuleResult, register_rule

REGULATION_CLAUSE_SECTION = "3.2.5.1"


class FireExtinguisherRule(Rule):
    rule_id = "fire-extinguisher-travel-distance"

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
            elif travel_distance <= maximum_m:
                passed = True
                message = (
                    f"Fire extinguisher {item_id} ({location}) travel distance "
                    f"{travel_distance}m is within the maximum of "
                    f"{maximum_m}m."
                )
            else:
                passed = False
                message = (
                    f"Fire extinguisher {item_id} ({location}) travel distance "
                    f"{travel_distance}m exceeds the maximum of "
                    f"{maximum_m}m."
                )

            results.append(
                RuleResult(
                    rule_id=self.rule_id,
                    passed=passed,
                    message=message,
                    regulation_clause_id=clause.id,
                    evidence={
                        "fire_protection_item_id": item_id,
                        "item_type": item_type_value,
                        "travel_distance_to_nearest_m": travel_distance,
                        "maximum_m": maximum_m,
                        "regulation_clause_section": REGULATION_CLAUSE_SECTION,
                    },
                )
            )

        return results


# Retained for seed_regulations.py reference values.
MAX_FIRE_EXTINGUISHER_TRAVEL_DISTANCE_M = 23.0

fire_extinguisher_rule = register_rule(FireExtinguisherRule())
