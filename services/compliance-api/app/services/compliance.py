from dataclasses import asdict
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.rules.runner import run_all_rules
from app.schemas import ComplianceReport, ComplianceSummary, RuleResultRead


def build_compliance_report(project_id: int, db: Session) -> ComplianceReport:
    raw_results = run_all_rules(project_id, db)
    results = [RuleResultRead.model_validate(asdict(result)) for result in raw_results]
    passed = sum(1 for result in results if result.passed)
    failed = len(results) - passed

    return ComplianceReport(
        project_id=project_id,
        generated_at=datetime.now(UTC),
        results=results,
        summary=ComplianceSummary(passed=passed, failed=failed),
    )
