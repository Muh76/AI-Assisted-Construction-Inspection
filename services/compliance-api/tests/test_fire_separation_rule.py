from app.rules.base import rule_registry
from app.rules.fire_separation import FireSeparationRule


def test_fire_separation_rule_passing_and_failing():
    rule = FireSeparationRule()
    project_data = {
        "fire_protection_items": [
            {
                "id": 1,
                "item_type": "fire_separation",
                "location": "Tenant demising wall",
                "rating_required": "120 min",
                "rating_provided": "120 min",
            },
            {
                "id": 2,
                "item_type": "fire_separation",
                "location": "Stair enclosure",
                "rating_required": "120 min",
                "rating_provided": "90 min",
            },
            {
                "id": 3,
                "item_type": "penetration_seal",
                "location": "Shaft wall",
                "rating_required": "60 min",
                "rating_provided": "30 min",
            },
        ]
    }

    results = rule.evaluate(project_data)

    assert len(results) == 2

    passing, failing = results
    assert passing.passed is True
    assert passing.rule_id == "fire-separation-rating"
    assert passing.evidence["fire_protection_item_id"] == 1
    assert passing.evidence["required_minutes"] == 120
    assert passing.evidence["provided_minutes"] == 120

    assert failing.passed is False
    assert failing.rule_id == "fire-separation-rating"
    assert failing.evidence["fire_protection_item_id"] == 2
    assert failing.evidence["required_minutes"] == 120
    assert failing.evidence["provided_minutes"] == 90
    assert "below the required" in failing.message


def test_fire_separation_rule_is_registered():
    assert rule_registry.get("fire-separation-rating") is not None
