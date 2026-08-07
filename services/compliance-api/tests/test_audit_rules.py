from scripts.audit_rules import _load_seed_todo_sections, audit_placeholder_clauses
from app.models import RegulationClause


def test_load_seed_todo_sections_matches_seed_script():
    sections = _load_seed_todo_sections()

    assert sections == frozenset(
        {
            "3.4.7.1",
            "3.4.7.2",
            "3.4.2.7",
            "3.4.2.1",
            "3.2.2.1",
            "3.2.5.1",
            "3.1.9.4",
            "3.1.3.2",
            "3.1.2.1",
        }
    )


def test_audit_placeholder_clauses_reports_null_threshold_and_seed_sections(
    db_session,
    monkeypatch,
):
    db_session.add_all(
        [
            RegulationClause(
                code="OBC",
                section="3.2.2.1",
                title="Automatic sprinkler coverage",
                description="Placeholder",
                threshold_value=None,
                threshold_unit=None,
            ),
            RegulationClause(
                code="OBC",
                section="3.4.7.1",
                title="Minimum door clear width",
                description="Updated from uploaded document",
                threshold_value=860.0,
                threshold_unit="mm",
            ),
            RegulationClause(
                code="OBC",
                section="9.9.9.9",
                title="Custom clause",
                description="Added manually",
                threshold_value=42.0,
                threshold_unit="mm",
            ),
        ]
    )
    db_session.commit()

    monkeypatch.setattr(
        "scripts.audit_rules.SessionLocal",
        lambda: db_session,
    )

    placeholders = audit_placeholder_clauses()

    assert len(placeholders) == 2
    assert {item.section for item in placeholders} == {"3.2.2.1", "3.4.7.1"}

    sprinkler = next(item for item in placeholders if item.section == "3.2.2.1")
    assert sprinkler.reasons == ("null_threshold_value", "seed_todo_section")

    door = next(item for item in placeholders if item.section == "3.4.7.1")
    assert door.reasons == ("seed_todo_section",)
