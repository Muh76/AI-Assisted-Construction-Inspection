import math

from tests.rule_test_helpers import regulation_clause_lookup_for
from app.rules.base import rule_registry
from app.rules.occupant_load import (
    OCCUPANT_LOAD_FACTORS_SQM_PER_PERSON,
    REGULATION_CLAUSE_SECTION,
    OccupantLoadRule,
)


def test_occupant_load_rule_passing_and_failing():
    rule = OccupantLoadRule()
    load_factor = OCCUPANT_LOAD_FACTORS_SQM_PER_PERSON["office"]
    floor_area = load_factor * 2  # 18.6 sqm -> expected load 2

    project_data = {
        "rooms": [
            {
                "id": 1,
                "name": "Private Office",
                "occupancy_category": "office",
                "floor_area": floor_area,
                "occupant_load": math.ceil(floor_area / load_factor),
            },
            {
                "id": 2,
                "name": "Reception",
                "occupancy_category": "office",
                "floor_area": floor_area,
                "occupant_load": 10,
            },
        ]
    }

    results = rule.evaluate(
        project_data,
        regulation_clause_lookup_for(
            REGULATION_CLAUSE_SECTION,
            threshold_value=load_factor,
        ),
    )

    assert len(results) == 2

    passing, failing = results
    assert passing.passed is True
    assert passing.rule_id == "occupant-load"
    assert passing.regulation_clause_id == 1
    assert passing.evidence["room_id"] == 1
    assert passing.evidence["expected_occupant_load"] == 2
    assert passing.evidence["load_factor_sqm_per_person"] == 9.3

    assert failing.passed is False
    assert failing.rule_id == "occupant-load"
    assert failing.regulation_clause_id == 1
    assert failing.evidence["room_id"] == 2
    assert failing.evidence["expected_occupant_load"] == 2
    assert failing.evidence["occupant_load"] == 10
    assert "does not match" in failing.message


def test_occupant_load_rule_unknown_category():
    rule = OccupantLoadRule()
    results = rule.evaluate(
        {
            "rooms": [
                {
                    "id": 3,
                    "name": "Storage",
                    "occupancy_category": "unknown",
                    "floor_area": 20.0,
                    "occupant_load": 1,
                }
            ]
        },
        regulation_clause_lookup_for(
            REGULATION_CLAUSE_SECTION,
            threshold_value=OCCUPANT_LOAD_FACTORS_SQM_PER_PERSON["office"],
        ),
    )

    assert len(results) == 1
    assert results[0].passed is False
    assert results[0].regulation_clause_id == 1
    assert "unknown occupancy category" in results[0].message


def test_occupant_load_rule_is_registered():
    assert rule_registry.get("occupant-load") is not None
