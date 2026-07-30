from app.rules.base import rule_registry
from app.rules.door_width import MIN_DOOR_CLEAR_WIDTH_MM, DoorWidthRule


def test_door_width_rule_passing_and_failing():
    rule = DoorWidthRule()
    project_data = {
        "doors": [
            {"id": 1, "clear_width": 860.0, "room_id": 1},
            {"id": 2, "clear_width": 750.0, "room_id": 2},
        ]
    }

    results = rule.evaluate(project_data)

    assert len(results) == 2

    passing, failing = results
    assert passing.passed is True
    assert passing.rule_id == "door-min-width"
    assert passing.evidence["door_id"] == 1
    assert passing.evidence["clear_width_mm"] == 860.0
    assert passing.evidence["minimum_mm"] == MIN_DOOR_CLEAR_WIDTH_MM

    assert failing.passed is False
    assert failing.rule_id == "door-min-width"
    assert failing.evidence["door_id"] == 2
    assert failing.evidence["clear_width_mm"] == 750.0
    assert "below the minimum" in failing.message


def test_door_width_rule_is_registered():
    assert rule_registry.get("door-min-width") is not None
