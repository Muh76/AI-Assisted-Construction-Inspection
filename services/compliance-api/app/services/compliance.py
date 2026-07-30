from dataclasses import asdict
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import RegulationClause
from app.rules.runner import run_all_rules
from app.schemas import ComplianceReport, ComplianceSummary, RuleResultRead


def format_regulation_citation(clause: RegulationClause) -> str:
    return f"{clause.code} {clause.section}"


def build_compliance_report(project_id: int, db: Session) -> ComplianceReport:
    raw_results = run_all_rules(project_id, db)

    clause_ids = {
        result.regulation_clause_id
        for result in raw_results
        if result.regulation_clause_id is not None
    }
    clauses_by_id: dict[int, RegulationClause] = {}
    if clause_ids:
        clauses = db.scalars(
            select(RegulationClause).where(RegulationClause.id.in_(clause_ids))
        ).all()
        clauses_by_id = {clause.id: clause for clause in clauses}

    results: list[RuleResultRead] = []
    for result in raw_results:
        payload = asdict(result)
        clause_id = payload.get("regulation_clause_id")
        clause = clauses_by_id.get(clause_id) if clause_id is not None else None
        payload["regulation_citation"] = (
            format_regulation_citation(clause) if clause is not None else None
        )
        results.append(RuleResultRead.model_validate(payload))

    passed = sum(1 for result in results if result.passed)
    failed = len(results) - passed

    return ComplianceReport(
        project_id=project_id,
        generated_at=datetime.now(UTC),
        results=results,
        summary=ComplianceSummary(passed=passed, failed=failed),
    )
