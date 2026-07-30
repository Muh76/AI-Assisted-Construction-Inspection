from app.rules.base import rule_registry
from app.rules.sprinkler_coverage import SprinklerCoverageRule


def test_sprinkler_coverage_rule_passing_and_failing():
    rule = SprinklerCoverageRule()
    project_data = {
        "rooms": [
            {"id": 1, "name": "Open Office", "sprinklered": True},
            {"id": 2, "name": "Storage", "sprinklered": False},
        ]
    }

    results = rule.evaluate(project_data)

    assert len(results) == 2

    passing, failing = results
    assert passing.passed is True
    assert passing.rule_id == "sprinkler-coverage"
    assert passing.evidence["room_id"] == 1
    assert passing.evidence["sprinklered"] is True
    assert "is sprinklered" in passing.message

    assert failing.passed is False
    assert failing.rule_id == "sprinkler-coverage"
    assert failing.evidence["room_id"] == 2
    assert failing.evidence["sprinklered"] is False
    assert "is not sprinklered" in failing.message


def test_sprinkler_coverage_rule_is_registered():
    assert rule_registry.get("sprinkler-coverage") is not None
