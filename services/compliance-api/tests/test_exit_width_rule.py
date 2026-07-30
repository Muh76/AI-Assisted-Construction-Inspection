from tests.conftest import noop_regulation_clause_lookup
from app.rules.base import rule_registry
from app.rules.exit_width import MIN_EXIT_CLEAR_WIDTH_MM, ExitWidthRule


def test_exit_width_rule_passing_and_failing():
    rule = ExitWidthRule()
    project_data = {
        "exits": [
            {"id": 1, "clear_width": 1200.0, "location": "North stair"},
            {"id": 2, "clear_width": 1050.0, "location": "South stair"},
        ]
    }

    results = rule.evaluate(project_data, noop_regulation_clause_lookup)

    assert len(results) == 2

    passing, failing = results
    assert passing.passed is True
    assert passing.rule_id == "exit-min-width"
    assert passing.evidence["exit_id"] == 1
    assert passing.evidence["clear_width_mm"] == 1200.0
    assert passing.evidence["minimum_mm"] == MIN_EXIT_CLEAR_WIDTH_MM

    assert failing.passed is False
    assert failing.rule_id == "exit-min-width"
    assert failing.evidence["exit_id"] == 2
    assert failing.evidence["clear_width_mm"] == 1050.0
    assert "below the minimum" in failing.message


def test_exit_width_rule_is_registered():
    assert rule_registry.get("exit-min-width") is not None
