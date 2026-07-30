import app.rules  # noqa: F401 — ensure registered rules are loaded
from app.rules.base import RuleResult
from app.rules.runner import run_all_rules


def test_run_all_rules_returns_results(db_session):
    from datetime import UTC, datetime

    from app.auth.security import hash_password
    from app.models import Corridor, Door, Project, Room, User

    user = User(
        email="runner@example.com",
        hashed_password=hash_password("test-password"),
        created_at=datetime.now(UTC).replace(tzinfo=None),
    )
    db_session.add(user)
    db_session.flush()

    project = Project(name="Runner Test", owner_id=user.id)
    db_session.add(project)
    db_session.flush()

    room = Room(
        project_id=project.id,
        name="Office",
        occupancy_category="office",
        floor_area=18.6,
        occupant_load=2,
    )
    db_session.add(room)
    db_session.flush()

    db_session.add_all(
        [
            Door(room_id=room.id, clear_width=860.0),
            Corridor(project_id=project.id, clear_width=900.0, length=10.0),
        ]
    )
    db_session.commit()

    results = run_all_rules(project.id, db_session)

    assert all(isinstance(result, RuleResult) for result in results)
    assert len(results) >= 3
    assert any(not result.passed and result.rule_id == "corridor-min-width" for result in results)
