from app.rules.base import rule_registry
from app.rules.penetrations import PenetrationsRule


def test_penetrations_rule_passing_and_failing():
    rule = PenetrationsRule()
    project_data = {
        "fire_protection_items": [
            {
                "id": 1,
                "item_type": "penetration_seal",
                "location": "Shaft wall L2",
                "rating_required": "60 min",
                "rating_provided": "90 min",
            },
            {
                "id": 2,
                "item_type": "penetration_seal",
                "location": "Service riser",
                "rating_required": "60 min",
                "rating_provided": "45 min",
            },
            {
                "id": 3,
                "item_type": "fire_extinguisher",
                "location": "Corridor A",
                "rating_required": "60 min",
                "rating_provided": "30 min",
            },
        ]
    }

    results = rule.evaluate(project_data)

    assert len(results) == 2

    passing, failing = results
    assert passing.passed is True
    assert passing.rule_id == "penetration-seal-rating"
    assert passing.evidence["fire_protection_item_id"] == 1
    assert passing.evidence["required_minutes"] == 60
    assert passing.evidence["provided_minutes"] == 90

    assert failing.passed is False
    assert failing.rule_id == "penetration-seal-rating"
    assert failing.evidence["fire_protection_item_id"] == 2
    assert failing.evidence["required_minutes"] == 60
    assert failing.evidence["provided_minutes"] == 45
    assert "below the required" in failing.message


def test_penetrations_rule_is_registered():
    assert rule_registry.get("penetration-seal-rating") is not None
