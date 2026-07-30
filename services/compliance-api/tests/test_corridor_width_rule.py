from types import SimpleNamespace

from app.models import RegulationClause
from app.rules.base import rule_registry
from app.rules.corridor_width import (
    MIN_CORRIDOR_CLEAR_WIDTH_MM,
    REGULATION_CLAUSE_SECTION,
    CorridorWidthRule,
)
from app.rules.runner import build_regulation_clause_lookup


def _lookup_for_threshold(threshold_value: float, clause_id: int = 1):
    clause = SimpleNamespace(id=clause_id, threshold_value=threshold_value)

    def lookup(section: str):
        if section == REGULATION_CLAUSE_SECTION:
            return clause
        return None

    return lookup


def test_corridor_width_rule_passing_and_failing():
    rule = CorridorWidthRule()
    project_data = {
        "corridors": [
            {"id": 1, "clear_width": 1100.0, "length": 18.5},
            {"id": 2, "clear_width": 900.0, "length": 12.0},
        ]
    }

    results = rule.evaluate(project_data, _lookup_for_threshold(MIN_CORRIDOR_CLEAR_WIDTH_MM))

    assert len(results) == 2

    passing, failing = results
    assert passing.passed is True
    assert passing.rule_id == "corridor-min-width"
    assert passing.regulation_clause_id == 1
    assert passing.evidence["corridor_id"] == 1
    assert passing.evidence["clear_width_mm"] == 1100.0
    assert passing.evidence["minimum_mm"] == MIN_CORRIDOR_CLEAR_WIDTH_MM

    assert failing.passed is False
    assert failing.rule_id == "corridor-min-width"
    assert failing.regulation_clause_id == 1
    assert failing.evidence["corridor_id"] == 2
    assert failing.evidence["clear_width_mm"] == 900.0
    assert "below the minimum" in failing.message


def test_corridor_width_rule_is_registered():
    assert rule_registry.get("corridor-min-width") is not None


def test_corridor_width_rule_uses_database_threshold(db_session):
    clause = RegulationClause(
        code="OBC",
        section=REGULATION_CLAUSE_SECTION,
        title="Minimum corridor clear width",
        description="Test corridor width threshold from database.",
        threshold_value=950.0,
        threshold_unit="mm",
    )
    db_session.add(clause)
    db_session.commit()

    rule = CorridorWidthRule()
    lookup = build_regulation_clause_lookup(db_session)
    results = rule.evaluate(
        {"corridors": [{"id": 1, "clear_width": 1000.0, "length": 10.0}]},
        lookup,
    )

    assert len(results) == 1
    result = results[0]
    assert result.passed is True
    assert result.regulation_clause_id == clause.id
    assert result.evidence["minimum_mm"] == 950.0
    assert result.evidence["minimum_mm"] != MIN_CORRIDOR_CLEAR_WIDTH_MM
