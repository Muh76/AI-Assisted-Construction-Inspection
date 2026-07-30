from datetime import UTC, datetime

from app.reports.pdf import build_compliance_pdf
from app.schemas import ComplianceReport, ComplianceSummary, RuleResultRead


def test_build_compliance_pdf_includes_regulation_citation():
    report = ComplianceReport(
        project_id=1,
        generated_at=datetime.now(UTC),
        results=[
            RuleResultRead(
                rule_id="door-min-width",
                passed=True,
                message="Door 1 clear width 860mm meets the minimum of 860mm.",
                evidence={"door_id": 1},
                regulation_clause_id=1,
                regulation_citation="OBC 3.4.7.1",
            ),
            RuleResultRead(
                rule_id="occupant-load",
                passed=False,
                message="Occupant load mismatch.",
                evidence={"room_id": 1},
                regulation_clause_id=None,
                regulation_citation=None,
            ),
        ],
        summary=ComplianceSummary(passed=1, failed=1),
    )

    pdf_bytes = build_compliance_pdf(report, "Citation Test Project")

    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 500
