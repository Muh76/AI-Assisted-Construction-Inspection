from app.rules.corridor_width import CorridorWidthRule, MIN_CORRIDOR_CLEAR_WIDTH_MM
from app.rules.base import rule_registry


def test_corridor_width_rule_passing_and_failing():
    rule = CorridorWidthRule()
    project_data = {
        "corridors": [
            {"id": 1, "clear_width": 1100.0, "length": 18.5},
            {"id": 2, "clear_width": 900.0, "length": 12.0},
        ]
    }

    results = rule.evaluate(project_data)

    assert len(results) == 2

    passing, failing = results
    assert passing.passed is True
    assert passing.rule_id == "corridor-min-width"
    assert passing.evidence["corridor_id"] == 1
    assert passing.evidence["clear_width_mm"] == 1100.0
    assert passing.evidence["minimum_mm"] == MIN_CORRIDOR_CLEAR_WIDTH_MM

    assert failing.passed is False
    assert failing.rule_id == "corridor-min-width"
    assert failing.evidence["corridor_id"] == 2
    assert failing.evidence["clear_width_mm"] == 900.0
    assert "below the minimum" in failing.message


def test_corridor_width_rule_is_registered():
    assert rule_registry.get("corridor-min-width") is not None
