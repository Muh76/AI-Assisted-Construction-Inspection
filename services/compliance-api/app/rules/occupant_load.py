import math
from typing import Any

from app.rules.base import RegulationClauseLookup, Rule, RuleResult, register_rule

REGULATION_CLAUSE_SECTION = "3.1.2.1"
SUPPORTED_OCCUPANCY_CATEGORIES = {"office", "b"}


class OccupantLoadRule(Rule):
    rule_id = "occupant-load"

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

        load_factor = clause.threshold_value
        rooms = project_data.get("rooms", [])
        results: list[RuleResult] = []

        for room in rooms:
            if isinstance(room, dict):
                room_id = room["id"]
                name = room.get("name", str(room_id))
                occupancy_category = room["occupancy_category"]
                floor_area = room["floor_area"]
                occupant_load = room["occupant_load"]
            else:
                room_id = room.id
                name = room.name
                occupancy_category = room.occupancy_category
                floor_area = room.floor_area
                occupant_load = room.occupant_load

            category_key = occupancy_category.strip().lower()
            if category_key not in SUPPORTED_OCCUPANCY_CATEGORIES:
                results.append(
                    RuleResult(
                        rule_id=self.rule_id,
                        passed=False,
                        message=(
                            f"Room {room_id} ({name}) uses unknown occupancy category "
                            f"'{occupancy_category}'."
                        ),
                        regulation_clause_id=clause.id,
                        evidence={
                            "room_id": room_id,
                            "occupancy_category": occupancy_category,
                            "floor_area_sqm": floor_area,
                            "occupant_load": occupant_load,
                            "regulation_clause_section": REGULATION_CLAUSE_SECTION,
                        },
                    )
                )
                continue

            expected_load = math.ceil(floor_area / load_factor)
            passed = occupant_load == expected_load

            if passed:
                message = (
                    f"Room {room_id} ({name}) occupant load {occupant_load} matches the "
                    f"expected load of {expected_load} for {floor_area} sqm at "
                    f"{load_factor} sqm per person."
                )
            else:
                message = (
                    f"Room {room_id} ({name}) occupant load {occupant_load} does not match "
                    f"the expected load of {expected_load} for {floor_area} sqm at "
                    f"{load_factor} sqm per person."
                )

            results.append(
                RuleResult(
                    rule_id=self.rule_id,
                    passed=passed,
                    message=message,
                    regulation_clause_id=clause.id,
                    evidence={
                        "room_id": room_id,
                        "occupancy_category": occupancy_category,
                        "floor_area_sqm": floor_area,
                        "occupant_load": occupant_load,
                        "expected_occupant_load": expected_load,
                        "load_factor_sqm_per_person": load_factor,
                        "regulation_clause_section": REGULATION_CLAUSE_SECTION,
                    },
                )
            )

        return results


# Retained for seed_regulations.py reference values.
OCCUPANT_LOAD_FACTORS_SQM_PER_PERSON: dict[str, float] = {
    "office": 9.3,
    "B": 9.3,
}

occupant_load_rule = register_rule(OccupantLoadRule())
