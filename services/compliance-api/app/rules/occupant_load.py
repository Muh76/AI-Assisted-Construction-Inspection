import math
from typing import Any

from app.rules.base import Rule, RuleResult, register_rule

# Square metres of floor area per occupant (placeholder lookup).
OCCUPANT_LOAD_FACTORS_SQM_PER_PERSON: dict[str, float] = {
    "office": 9.3,
    "B": 9.3,
}


class OccupantLoadRule(Rule):
    rule_id = "occupant-load"

    def evaluate(self, project_data: Any) -> list[RuleResult]:
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

            category_key = occupancy_category.strip()
            load_factor = OCCUPANT_LOAD_FACTORS_SQM_PER_PERSON.get(
                category_key
            ) or OCCUPANT_LOAD_FACTORS_SQM_PER_PERSON.get(category_key.lower())

            if load_factor is None:
                results.append(
                    RuleResult(
                        rule_id=self.rule_id,
                        passed=False,
                        message=(
                            f"Room {room_id} ({name}) uses unknown occupancy category "
                            f"'{occupancy_category}'."
                        ),
                        evidence={
                            "room_id": room_id,
                            "occupancy_category": occupancy_category,
                            "floor_area_sqm": floor_area,
                            "occupant_load": occupant_load,
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
                    evidence={
                        "room_id": room_id,
                        "occupancy_category": occupancy_category,
                        "floor_area_sqm": floor_area,
                        "occupant_load": occupant_load,
                        "expected_occupant_load": expected_load,
                        "load_factor_sqm_per_person": load_factor,
                    },
                )
            )

        return results


occupant_load_rule = register_rule(OccupantLoadRule())
