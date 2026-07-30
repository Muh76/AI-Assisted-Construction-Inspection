from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class RuleResult:
    rule_id: str
    passed: bool
    message: str
    evidence: dict[str, Any] = field(default_factory=dict)


class Rule(ABC):
    rule_id: str

    @abstractmethod
    def evaluate(self, project_data: Any) -> list[RuleResult]:
        """Evaluate compliance for the given project data."""

    def register(self) -> None:
        rule_registry.register(self)


class RuleRegistry:
    def __init__(self) -> None:
        self._rules: dict[str, Rule] = {}

    def register(self, rule: Rule) -> None:
        self._rules[rule.rule_id] = rule

    def get(self, rule_id: str) -> Rule | None:
        return self._rules.get(rule_id)

    def all(self) -> list[Rule]:
        return list(self._rules.values())


rule_registry = RuleRegistry()


def register_rule(rule: Rule) -> Rule:
    """Register a rule instance and return it (for use as a decorator target)."""
    rule_registry.register(rule)
    return rule
