"""Print compliance rule results for the seeded sample project."""

import app.rules  # noqa: F401 — ensure registered rules are loaded
from sqlalchemy import select

from app.db import SessionLocal
from app.models import Project
from app.rules.base import rule_registry
from app.rules.runner import _load_project_data, run_all_rules

SAMPLE_PROJECT_NAME = "Riverside Office Fit-Out"


def main() -> None:
    db = SessionLocal()
    try:
        project = db.scalar(
            select(Project).where(Project.name == SAMPLE_PROJECT_NAME)
        )
        if project is None:
            print(f"Project not found: {SAMPLE_PROJECT_NAME!r}")
            print("Run: seed-example")
            raise SystemExit(1)

        registered_rule_ids = sorted(rule.rule_id for rule in rule_registry.all())
        print(f"Registered rules ({len(registered_rule_ids)}):")
        for rule_id in registered_rule_ids:
            print(f"  - {rule_id}")
        print()
        print(f"Project: {project.name} (id={project.id})")
        print()

        project_data = _load_project_data(project.id, db)
        if project_data is None:
            print("Failed to load project data.")
            raise SystemExit(1)

        for rule in rule_registry.all():
            rule.evaluate(project_data)

        results = run_all_rules(project.id, db)
        print(f"Rule results ({len(results)}):")
        for result in results:
            status = "PASS" if result.passed else "FAIL"
            print(f"  {result.rule_id}: {status}")

        result_rule_ids = {result.rule_id for result in results}
        silent_rule_ids = [
            rule_id for rule_id in registered_rule_ids if rule_id not in result_rule_ids
        ]
        if silent_rule_ids:
            print()
            print("Rules with no results (no matching entities):")
            for rule_id in silent_rule_ids:
                print(f"  - {rule_id}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
