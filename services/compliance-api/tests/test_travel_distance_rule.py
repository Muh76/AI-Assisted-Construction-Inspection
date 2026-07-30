from tests.rule_test_helpers import regulation_clause_lookup_for
from app.rules.base import rule_registry
from app.rules.travel_distance import (
    MAX_TRAVEL_DISTANCE_SPRINKLERED_M,
    REGULATION_CLAUSE_SECTION,
    TravelDistanceRule,
)


def test_travel_distance_rule_passing_and_failing():
    rule = TravelDistanceRule()
    project_data = {
        "rooms": [
            {
                "id": 1,
                "name": "Open Office",
                "travel_distance": 40.0,
            },
            {
                "id": 2,
                "name": "Storage",
                "travel_distance": 52.0,
            },
        ]
    }

    results = rule.evaluate(
        project_data,
        regulation_clause_lookup_for(
            REGULATION_CLAUSE_SECTION,
            threshold_value=MAX_TRAVEL_DISTANCE_SPRINKLERED_M,
        ),
    )

    assert len(results) == 2

    passing, failing = results
    assert passing.passed is True
    assert passing.rule_id == "travel-distance"
    assert passing.regulation_clause_id == 1
    assert passing.evidence["room_id"] == 1
    assert passing.evidence["travel_distance_m"] == 40.0
    assert passing.evidence["maximum_m"] == MAX_TRAVEL_DISTANCE_SPRINKLERED_M

    assert failing.passed is False
    assert failing.rule_id == "travel-distance"
    assert failing.regulation_clause_id == 1
    assert failing.evidence["room_id"] == 2
    assert failing.evidence["travel_distance_m"] == 52.0
    assert "exceeds the maximum" in failing.message


def test_travel_distance_rule_is_registered():
    assert rule_registry.get("travel-distance") is not None
