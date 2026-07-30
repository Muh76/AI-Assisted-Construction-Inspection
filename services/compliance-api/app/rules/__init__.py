from app.rules.base import Rule, RuleRegistry, RuleResult, RegulationClauseLookup, register_rule, rule_registry
from app.rules import (  # noqa: F401 — register rules
    corridor_width,
    door_width,
    exit_width,
    fire_extinguisher,
    fire_separation,
    occupant_load,
    penetrations,
    required_exits,
    sprinkler_coverage,
    travel_distance,
)

__all__ = [
    "Rule",
    "RuleRegistry",
    "RuleResult",
    "RegulationClauseLookup",
    "register_rule",
    "rule_registry",
]
