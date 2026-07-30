from tests.rule_test_helpers import regulation_clause_lookup_for
from app.rules.base import rule_registry
from app.rules.fire_extinguisher import (
    MAX_FIRE_EXTINGUISHER_TRAVEL_DISTANCE_M,
    FireExtinguisherRule,
    REGULATION_CLAUSE_SECTION,
)


def test_fire_extinguisher_rule_passing_and_failing():
    rule = FireExtinguisherRule()
    project_data = {
        "fire_protection_items": [
            {
                "id": 1,
                "item_type": "fire_extinguisher",
                "location": "Corridor A",
                "travel_distance_to_nearest": 18.0,
            },
            {
                "id": 2,
                "item_type": "fire_extinguisher",
                "location": "Corridor B",
                "travel_distance_to_nearest": 28.0,
            },
            {
                "id": 3,
                "item_type": "penetration_seal",
                "location": "Shaft wall",
                "travel_distance_to_nearest": 50.0,
            },
        ]
    }

    results = rule.evaluate(
        project_data,
        regulation_clause_lookup_for(
            REGULATION_CLAUSE_SECTION,
            threshold_value=MAX_FIRE_EXTINGUISHER_TRAVEL_DISTANCE_M,
        ),
    )

    assert len(results) == 2

    passing, failing = results
    assert passing.passed is True
    assert passing.rule_id == "fire-extinguisher-travel-distance"
    assert passing.regulation_clause_id == 1
    assert passing.evidence["fire_protection_item_id"] == 1
    assert passing.evidence["travel_distance_to_nearest_m"] == 18.0
    assert passing.evidence["maximum_m"] == MAX_FIRE_EXTINGUISHER_TRAVEL_DISTANCE_M

    assert failing.passed is False
    assert failing.rule_id == "fire-extinguisher-travel-distance"
    assert failing.regulation_clause_id == 1
    assert failing.evidence["fire_protection_item_id"] == 2
    assert failing.evidence["travel_distance_to_nearest_m"] == 28.0
    assert "exceeds the maximum" in failing.message


def test_fire_extinguisher_rule_is_registered():
    assert rule_registry.get("fire-extinguisher-travel-distance") is not None
