import math

from tests.conftest import noop_regulation_clause_lookup
from app.rules.base import rule_registry
from app.rules.occupant_load import (
    OCCUPANT_LOAD_FACTORS_SQM_PER_PERSON,
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

    results = rule.evaluate(project_data, noop_regulation_clause_lookup)

    assert len(results) == 2

    passing, failing = results
    assert passing.passed is True
    assert passing.rule_id == "occupant-load"
    assert passing.evidence["room_id"] == 1
    assert passing.evidence["expected_occupant_load"] == 2
    assert passing.evidence["load_factor_sqm_per_person"] == 9.3

    assert failing.passed is False
    assert failing.rule_id == "occupant-load"
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
        noop_regulation_clause_lookup,
    )

    assert len(results) == 1
    assert results[0].passed is False
    assert "unknown occupancy category" in results[0].message


def test_occupant_load_rule_is_registered():
    assert rule_registry.get("occupant-load") is not None
