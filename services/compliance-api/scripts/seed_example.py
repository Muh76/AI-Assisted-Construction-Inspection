"""Seed the local dev database with a sample compliance project."""

from datetime import UTC, datetime

from sqlalchemy import select

from app.auth.security import hash_password
from app.db import SessionLocal
from app.models import (
    Corridor,
    Door,
    Exit,
    FireProtectionItem,
    FireProtectionItemType,
    Project,
    Room,
    User,
)

SAMPLE_PROJECT_NAME = "Riverside Office Fit-Out"
SEED_USER_EMAIL = "seed@example.com"
SEED_USER_PASSWORD = "seed-password-change-me"


def _get_or_create_seed_user(db) -> User:
    user = db.scalar(select(User).where(User.email == SEED_USER_EMAIL))
    if user is not None:
        return user

    user = User(
        email=SEED_USER_EMAIL,
        hashed_password=hash_password(SEED_USER_PASSWORD),
        created_at=datetime.now(UTC).replace(tzinfo=None),
    )
    db.add(user)
    db.flush()
    print(f"Created seed user id={user.id}: {SEED_USER_EMAIL}")
    return user


def seed() -> None:
    db = SessionLocal()

    try:
        existing = db.scalar(
            select(Project).where(Project.name == SAMPLE_PROJECT_NAME)
        )
        if existing is not None:
            print(f"Sample project already exists (id={existing.id}). Skipping seed.")
            return

        owner = _get_or_create_seed_user(db)

        project = Project(name=SAMPLE_PROJECT_NAME, owner_id=owner.id)
        db.add(project)
        db.flush()

        reception = Room(
            project_id=project.id,
            name="Reception",
            occupancy_category="B",
            floor_area=42.0,
            occupant_load=14,
            travel_distance=28.5,
            sprinklered=True,
        )
        private_office = Room(
            project_id=project.id,
            name="Private Office",
            occupancy_category="B",
            floor_area=12.5,
            occupant_load=2,
            travel_distance=18.0,
            sprinklered=True,
        )
        meeting_room = Room(
            project_id=project.id,
            name="Meeting Room",
            occupancy_category="B",
            floor_area=24.0,
            occupant_load=8,
            travel_distance=22.0,
            sprinklered=False,
        )
        db.add_all([reception, private_office, meeting_room])
        db.flush()

        db.add_all(
            [
                Door(
                    room_id=reception.id,
                    clear_width=860.0,
                    fire_rating="30 min",
                ),
                Door(
                    room_id=private_office.id,
                    clear_width=860.0,
                    fire_rating="30 min",
                ),
            ]
        )

        db.add(
            Corridor(
                project_id=project.id,
                clear_width=1100.0,
                length=18.5,
            )
        )

        db.add(
            Exit(
                project_id=project.id,
                location="North stair exit",
                clear_width=1050.0,
                is_required_exit=True,
            )
        )

        db.add_all(
            [
                FireProtectionItem(
                    project_id=project.id,
                    item_type=FireProtectionItemType.FIRE_EXTINGUISHER,
                    location="Reception lobby wall",
                    travel_distance_to_nearest=12.0,
                ),
                FireProtectionItem(
                    project_id=project.id,
                    item_type=FireProtectionItemType.PENETRATION_SEAL,
                    location="Level 1 mechanical riser",
                    rating_required="2 hr",
                    rating_provided="2 hr",
                ),
            ]
        )

        db.commit()

        print(f"Seeded project id={project.id}: {SAMPLE_PROJECT_NAME}")
        print(f"  Owner: {owner.email} (id={owner.id})")
        print(f"  Rooms: {reception.name}, {private_office.name}, {meeting_room.name}")
        print("  Doors: 2 x 860 mm clear width")
        print("  Corridors: 1 x 1100 mm clear width, 18.5 m length")
        print("  Exits: 1 required exit at north stair")
        print("  Fire protection items: 1 extinguisher, 1 penetration seal")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> None:
    seed()


if __name__ == "__main__":
    main()
