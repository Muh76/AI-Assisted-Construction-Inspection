"""Audit compliance rules for regulation clause wiring."""

from __future__ import annotations

import inspect
import re
from dataclasses import dataclass
from types import SimpleNamespace

import app.rules  # noqa: F401 — load registered rules
from app.rules.base import Rule, rule_registry

HARDCODED_THRESHOLD_PATTERN = re.compile(
    r"\b("
    r"MIN_[A-Z0-9_]+|"
    r"MAX_[A-Z0-9_]+|"
    r"OCCUPANT_LOAD_FACTORS(?:_[A-Z0-9_]+)?|"
    r"OCCUPANT_LOAD_EXIT_THRESHOLD"
    r")\b"
)

ALLOWED_HARDCODED_BY_RULE: dict[str, set[str]] = {
    # Exit counts are structural logic; occupant threshold comes from the clause.
    "required-exits": {"MIN_EXITS_ABOVE_THRESHOLD", "MIN_EXITS_AT_OR_BELOW_THRESHOLD"},
}

SAMPLE_PROJECT_DATA: dict[str, dict] = {
    "corridor-min-width": {
        "corridors": [{"id": 1, "clear_width": 1000.0, "length": 10.0}],
    },
    "door-min-width": {
        "doors": [{"id": 1, "clear_width": 900.0, "fire_rating": "30 min"}],
    },
    "exit-min-width": {
        "exits": [{"id": 1, "clear_width": 1200.0, "location": "North"}],
    },
    "travel-distance": {
        "rooms": [{"id": 1, "name": "Office", "travel_distance": 30.0}],
    },
    "required-exits": {
        "rooms": [{"id": 1, "occupant_load": 30}],
        "exits": [{"id": 1, "location": "North"}],
    },
    "sprinkler-coverage": {
        "rooms": [{"id": 1, "name": "Office", "sprinklered": True}],
    },
    "fire-extinguisher-travel-distance": {
        "fire_protection_items": [
            {
                "id": 1,
                "item_type": "fire_extinguisher",
                "location": "Corridor",
                "travel_distance_to_nearest": 10.0,
            }
        ],
    },
    "penetration-seal-rating": {
        "fire_protection_items": [
            {
                "id": 1,
                "item_type": "penetration_seal",
                "location": "Shaft",
                "rating_required": "60 min",
                "rating_provided": "60 min",
            }
        ],
    },
    "fire-separation-rating": {
        "fire_protection_items": [
            {
                "id": 1,
                "item_type": "fire_separation",
                "location": "Wall",
                "rating_required": "60 min",
                "rating_provided": "60 min",
            }
        ],
    },
    "occupant-load": {
        "rooms": [
            {
                "id": 1,
                "name": "Office",
                "occupancy_category": "office",
                "floor_area": 18.6,
                "occupant_load": 2,
            }
        ],
    },
}


@dataclass(frozen=True)
class RuleAuditResult:
    rule_id: str
    module_name: str
    uses_clause_lookup: bool
    sets_regulation_clause_id: bool
    hardcoded_thresholds: tuple[str, ...]
    runtime_sets_clause_id: bool

    @property
    def passed(self) -> bool:
        return (
            self.uses_clause_lookup
            and self.sets_regulation_clause_id
            and not self.hardcoded_thresholds
            and self.runtime_sets_clause_id
        )


def _rule_module_name(rule: Rule) -> str:
    return rule.__class__.__module__.rsplit(".", 1)[-1]


def _evaluate_source(rule: Rule) -> str:
    return inspect.getsource(rule.evaluate)


def _find_hardcoded_thresholds(rule_id: str, source: str) -> tuple[str, ...]:
    matches = sorted(set(HARDCODED_THRESHOLD_PATTERN.findall(source)))
    allowed = ALLOWED_HARDCODED_BY_RULE.get(rule_id, set())
    return tuple(match for match in matches if match not in allowed)


def _mock_lookup(_section: str) -> SimpleNamespace:
    return SimpleNamespace(id=1, threshold_value=100.0)


def _runtime_sets_clause_id(rule: Rule) -> bool:
    project_data = SAMPLE_PROJECT_DATA.get(rule.rule_id, {})
    results = rule.evaluate(project_data, _mock_lookup)
    if not results:
        return False
    return all(result.regulation_clause_id is not None for result in results)


def audit_rule(rule: Rule) -> RuleAuditResult:
    module_name = _rule_module_name(rule)
    source = _evaluate_source(rule)
    hardcoded = _find_hardcoded_thresholds(rule.rule_id, source)

    return RuleAuditResult(
        rule_id=rule.rule_id,
        module_name=module_name,
        uses_clause_lookup="lookup_regulation_clause(" in source,
        sets_regulation_clause_id="regulation_clause_id=" in source,
        hardcoded_thresholds=hardcoded,
        runtime_sets_clause_id=_runtime_sets_clause_id(rule),
    )


def audit_all_rules() -> list[RuleAuditResult]:
    return [audit_rule(rule) for rule in sorted(rule_registry.all(), key=lambda r: r.rule_id)]


def _print_report(results: list[RuleAuditResult]) -> int:
    print("Compliance rule regulation clause audit")
    print("=" * 72)

    failures = 0
    for result in results:
        status = "PASS" if result.passed else "FAIL"
        if not result.passed:
            failures += 1

        print(f"[{status}] {result.rule_id} ({result.module_name}.py)")
        print(
            f"       lookup_regulation_clause: "
            f"{'yes' if result.uses_clause_lookup else 'no'}"
        )
        print(
            f"       regulation_clause_id set: "
            f"{'yes' if result.sets_regulation_clause_id else 'no'}"
        )
        print(
            f"       runtime regulation_clause_id: "
            f"{'yes' if result.runtime_sets_clause_id else 'no'}"
        )
        if result.hardcoded_thresholds:
            joined = ", ".join(result.hardcoded_thresholds)
            print(f"       hardcoded threshold refs: {joined}")
        else:
            print("       hardcoded threshold refs: none")
        print()

    passed_count = len(results) - failures
    print("=" * 72)
    print(f"Summary: {passed_count} passed, {failures} failed, {len(results)} total")
    return 1 if failures else 0


def main() -> None:
    exit_code = _print_report(audit_all_rules())
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
