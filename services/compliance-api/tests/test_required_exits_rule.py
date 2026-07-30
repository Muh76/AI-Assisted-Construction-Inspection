from tests.rule_test_helpers import regulation_clause_lookup_for
from app.rules.base import rule_registry
from app.rules.required_exits import (
    MIN_EXITS_ABOVE_THRESHOLD,
    MIN_EXITS_AT_OR_BELOW_THRESHOLD,
    OCCUPANT_LOAD_EXIT_THRESHOLD,
    REGULATION_CLAUSE_SECTION,
    RequiredExitsRule,
)


def test_required_exits_rule_at_or_below_threshold():
    rule = RequiredExitsRule()
    project_data = {
        "rooms": [
            {"id": 1, "occupant_load": 30},
            {"id": 2, "occupant_load": 30},
        ],
        "exits": [{"id": 1, "location": "North stair"}],
    }

    results = rule.evaluate(
        project_data,
        regulation_clause_lookup_for(
            REGULATION_CLAUSE_SECTION,
            threshold_value=float(OCCUPANT_LOAD_EXIT_THRESHOLD),
        ),
    )

    assert len(results) == 1
    result = results[0]
    assert result.passed is True
    assert result.rule_id == "required-exits"
    assert result.regulation_clause_id == 1
    assert result.evidence["total_occupant_load"] == 60
    assert result.evidence["exit_count"] == 1
    assert result.evidence["required_exits"] == MIN_EXITS_AT_OR_BELOW_THRESHOLD
    assert result.evidence["occupant_threshold"] == OCCUPANT_LOAD_EXIT_THRESHOLD


def test_required_exits_rule_above_threshold():
    rule = RequiredExitsRule()
    lookup = regulation_clause_lookup_for(
        REGULATION_CLAUSE_SECTION,
        threshold_value=float(OCCUPANT_LOAD_EXIT_THRESHOLD),
    )

    passing_data = {
        "rooms": [
            {"id": 1, "occupant_load": 40},
            {"id": 2, "occupant_load": 25},
        ],
        "exits": [
            {"id": 1, "location": "North stair"},
            {"id": 2, "location": "South stair"},
        ],
    }
    failing_data = {
        "rooms": [
            {"id": 1, "occupant_load": 40},
            {"id": 2, "occupant_load": 25},
        ],
        "exits": [{"id": 1, "location": "North stair"}],
    }

    passing_result = rule.evaluate(passing_data, lookup)[0]
    failing_result = rule.evaluate(failing_data, lookup)[0]

    assert passing_result.passed is True
    assert passing_result.regulation_clause_id == 1
    assert passing_result.evidence["total_occupant_load"] == 65
    assert passing_result.evidence["exit_count"] == 2
    assert passing_result.evidence["required_exits"] == MIN_EXITS_ABOVE_THRESHOLD

    assert failing_result.passed is False
    assert failing_result.regulation_clause_id == 1
    assert failing_result.evidence["total_occupant_load"] == 65
    assert failing_result.evidence["exit_count"] == 1
    assert failing_result.evidence["required_exits"] == MIN_EXITS_ABOVE_THRESHOLD
    assert "requires at least" in failing_result.message


def test_required_exits_rule_is_registered():
    assert rule_registry.get("required-exits") is not None
