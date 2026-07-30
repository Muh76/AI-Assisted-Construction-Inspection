import re
from typing import Any

from app.models import FireProtectionItemType
from app.rules.base import RegulationClauseLookup, Rule, RuleResult, register_rule

REGULATION_CLAUSE_SECTION = "3.1.9.4"

_RATING_MINUTES_PATTERN = re.compile(r"(\d+)")


def _parse_rating_minutes(rating: str | None) -> int | None:
    if rating is None:
        return None
    match = _RATING_MINUTES_PATTERN.search(rating.strip())
    if match is None:
        return None
    return int(match.group(1))


class PenetrationsRule(Rule):
    rule_id = "penetration-seal-rating"

    def evaluate(
        self,
        project_data: Any,
        lookup_regulation_clause: RegulationClauseLookup,
    ) -> list[RuleResult]:
        clause = lookup_regulation_clause(REGULATION_CLAUSE_SECTION)
        if clause is None:
            return [
                RuleResult(
                    rule_id=self.rule_id,
                    passed=False,
                    message=(
                        f"Regulation clause {REGULATION_CLAUSE_SECTION} was not found."
                    ),
                )
            ]

        items = project_data.get("fire_protection_items", [])
        results: list[RuleResult] = []

        for item in items:
            if isinstance(item, dict):
                item_type = item["item_type"]
                item_id = item["id"]
                location = item.get("location", str(item_id))
                rating_required = item.get("rating_required")
                rating_provided = item.get("rating_provided")
            else:
                item_type = item.item_type
                item_id = item.id
                location = item.location
                rating_required = item.rating_required
                rating_provided = item.rating_provided

            if isinstance(item_type, FireProtectionItemType):
                item_type_value = item_type.value
            else:
                item_type_value = str(item_type)

            if item_type_value != FireProtectionItemType.PENETRATION_SEAL.value:
                continue

            required_minutes = _parse_rating_minutes(rating_required)
            provided_minutes = _parse_rating_minutes(rating_provided)

            if required_minutes is None or provided_minutes is None:
                passed = False
                message = (
                    f"Penetration seal {item_id} ({location}) has invalid or missing "
                    f"ratings (required: {rating_required!r}, provided: {rating_provided!r})."
                )
            elif provided_minutes >= required_minutes:
                passed = True
                message = (
                    f"Penetration seal {item_id} ({location}) provided rating "
                    f"{provided_minutes} min meets the required {required_minutes} min."
                )
            else:
                passed = False
                message = (
                    f"Penetration seal {item_id} ({location}) provided rating "
                    f"{provided_minutes} min is below the required {required_minutes} min."
                )

            results.append(
                RuleResult(
                    rule_id=self.rule_id,
                    passed=passed,
                    message=message,
                    regulation_clause_id=clause.id,
                    evidence={
                        "fire_protection_item_id": item_id,
                        "item_type": item_type_value,
                        "rating_required": rating_required,
                        "rating_provided": rating_provided,
                        "required_minutes": required_minutes,
                        "provided_minutes": provided_minutes,
                        "regulation_clause_section": REGULATION_CLAUSE_SECTION,
                    },
                )
            )

        return results


penetrations_rule = register_rule(PenetrationsRule())
