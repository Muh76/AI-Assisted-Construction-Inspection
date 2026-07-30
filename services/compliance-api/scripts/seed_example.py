"""Seed the local dev database with a sample compliance project."""

from sqlalchemy import select

from app.db import SessionLocal
from app.models import Corridor, Door, Project, Room

SAMPLE_PROJECT_NAME = "Riverside Office Fit-Out"


def seed() -> None:
    db = SessionLocal()

    try:
        existing = db.scalar(
            select(Project).where(Project.name == SAMPLE_PROJECT_NAME)
        )
        if existing is not None:
            print(f"Sample project already exists (id={existing.id}). Skipping seed.")
            return

        project = Project(name=SAMPLE_PROJECT_NAME)
        db.add(project)
        db.flush()

        reception = Room(
            project_id=project.id,
            name="Reception",
            occupancy_category="B",
            floor_area=42.0,
            occupant_load=14,
        )
        private_office = Room(
            project_id=project.id,
            name="Private Office",
            occupancy_category="B",
            floor_area=12.5,
            occupant_load=2,
        )
        meeting_room = Room(
            project_id=project.id,
            name="Meeting Room",
            occupancy_category="B",
            floor_area=24.0,
            occupant_load=8,
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

        db.commit()

        print(f"Seeded project id={project.id}: {SAMPLE_PROJECT_NAME}")
        print(f"  Rooms: {reception.name}, {private_office.name}, {meeting_room.name}")
        print("  Doors: 2 x 860 mm clear width")
        print("  Corridors: 1 x 1100 mm clear width, 18.5 m length")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> None:
    seed()


if __name__ == "__main__":
    main()
