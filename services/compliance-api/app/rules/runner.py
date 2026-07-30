from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

import app.rules  # noqa: F401 — ensure registered rules are loaded
from app.models import Door, Project, Room
from app.rules.base import RuleResult, rule_registry


def _load_project_data(project_id: int, db: Session) -> dict | None:
    project = db.scalar(
        select(Project)
        .where(Project.id == project_id)
        .options(
            selectinload(Project.rooms).selectinload(Room.doors),
            selectinload(Project.corridors),
        )
    )
    if project is None:
        return None

    doors: list[Door] = [door for room in project.rooms for door in room.doors]

    return {
        "project": project,
        "rooms": project.rooms,
        "corridors": project.corridors,
        "doors": doors,
    }


def run_all_rules(project_id: int, db: Session) -> list[RuleResult]:
    project_data = _load_project_data(project_id, db)
    if project_data is None:
        return []

    results: list[RuleResult] = []
    for rule in rule_registry.all():
        results.extend(rule.evaluate(project_data))
    return results
