from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

import app.rules  # noqa: F401 — ensure registered rules are loaded
from app.models import Door, Project, RegulationClause, Room
from app.rules.base import RegulationClauseLookup, RuleResult, rule_registry


def _load_project_data(project_id: int, db: Session) -> dict | None:
    project = db.scalar(
        select(Project)
        .where(Project.id == project_id)
        .options(
            selectinload(Project.rooms).selectinload(Room.doors),
            selectinload(Project.corridors),
            selectinload(Project.exits),
            selectinload(Project.fire_protection_items),
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
        "exits": project.exits,
        "fire_protection_items": project.fire_protection_items,
    }


def build_regulation_clause_lookup(db: Session) -> RegulationClauseLookup:
    clauses = db.scalars(select(RegulationClause)).all()
    clauses_by_section = {clause.section: clause for clause in clauses}

    def lookup_regulation_clause(section: str) -> RegulationClause | None:
        return clauses_by_section.get(section)

    return lookup_regulation_clause


def run_all_rules(project_id: int, db: Session) -> list[RuleResult]:
    project_data = _load_project_data(project_id, db)
    if project_data is None:
        return []

    lookup_regulation_clause = build_regulation_clause_lookup(db)
    results: list[RuleResult] = []
    for rule in rule_registry.all():
        results.extend(rule.evaluate(project_data, lookup_regulation_clause))
    return results
