"""Run the full extraction-to-compliance pipeline for manual sanity checking."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import app.rules  # noqa: F401 — ensure registered rules are loaded
import pdfplumber
from sqlalchemy import func, select

from app.db import SessionLocal
from app.models import Door, Project, RegulationClause, Room
from app.parsing.door_schedule import extract_door_schedule
from app.parsing.room_schedule import extract_room_schedule
from app.schemas import ComplianceReport
from app.services.compliance import build_compliance_report
from scripts.seed_example import _get_or_create_seed_user
from scripts.validate_extraction import _resolve_pdf_path, _upload_drawing

DEFAULT_PROJECT_PREFIX = "Full Pipeline Check"


def _log(message: str) -> None:
    print(message, file=sys.stderr)


def _create_fresh_project(db, owner, project_prefix: str) -> Project:
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    project = Project(name=f"{project_prefix} {timestamp}", owner_id=owner.id)
    db.add(project)
    db.flush()
    return project


def _count_pdf_pages(pdf_path: Path) -> int:
    with pdfplumber.open(pdf_path) as pdf:
        return len(pdf.pages)


def _auto_confirm_rooms(
    db,
    project_id: int,
    extracted_rooms: list[dict],
) -> list[Room]:
    created_rooms: list[Room] = []
    for row in extracted_rooms:
        room = Room(
            project_id=project_id,
            name=row["name"],
            occupancy_category=row["occupancy_category"],
            floor_area=row["floor_area"],
            occupant_load=row["occupant_load"],
        )
        db.add(room)
        created_rooms.append(room)

    db.flush()
    return created_rooms


def _auto_confirm_doors(
    db,
    extracted_doors: list[dict],
    rooms: list[Room],
) -> list[Door]:
    if not extracted_doors:
        return []

    if not rooms:
        _log(
            "Skipping door auto-confirm: no rooms were created to assign doors to."
        )
        return []

    created_doors: list[Door] = []
    for index, row in enumerate(extracted_doors):
        room = rooms[index % len(rooms)]
        door = Door(
            room_id=room.id,
            clear_width=row["width"],
            fire_rating=row.get("fire_rating"),
        )
        db.add(door)
        created_doors.append(door)

    db.flush()
    return created_doors


def _print_compliance_report(report: ComplianceReport) -> None:
    print("Compliance report")
    print("=" * 72)
    print(f"Project ID:   {report.project_id}")
    print(f"Generated at: {report.generated_at.isoformat()}")
    print(
        "Summary: "
        f"{report.summary.passed} passed, "
        f"{report.summary.failed} failed, "
        f"{len(report.results)} total results"
    )
    print("=" * 72)

    if not report.results:
        print("No rule results were produced.")
        return

    for result in report.results:
        status = "PASS" if result.passed else "FAIL"
        print(f"\n[{status}] {result.rule_id}")
        print(f"  Message:  {result.message}")
        if result.regulation_citation:
            print(f"  Citation: {result.regulation_citation}")
        if result.evidence:
            evidence_json = json.dumps(result.evidence, indent=2)
            print(f"  Evidence:\n{evidence_json}")

    print("\n" + "=" * 72)
    print("Full report JSON")
    print("=" * 72)
    print(report.model_dump_json(indent=2))


def run_full_pipeline_check(
    pdf_path: Path | None = None,
    door_page: int = 1,
    room_page: int = 1,
    project_prefix: str = DEFAULT_PROJECT_PREFIX,
) -> ComplianceReport:
    source_pdf = _resolve_pdf_path(pdf_path)
    page_count = _count_pdf_pages(source_pdf)

    _log(f"Using PDF: {source_pdf} ({page_count} pages)")
    _log(f"Door schedule page: {door_page}")
    _log(f"Room schedule page: {room_page}")

    db = SessionLocal()
    try:
        owner = _get_or_create_seed_user(db)
        project = _create_fresh_project(db, owner, project_prefix)
        drawing = _upload_drawing(db, project, source_pdf)
        db.commit()
        db.refresh(project)
        db.refresh(drawing)

        _log(f"Created fresh project id={project.id}: {project.name}")
        _log(f"Uploaded drawing id={drawing.id} -> {drawing.file_path}")

        extracted_doors = extract_door_schedule(drawing.id, door_page, db)
        extracted_rooms = extract_room_schedule(drawing.id, room_page, db)
        _log(
            "Extraction complete: "
            f"{len(extracted_doors)} door row(s), {len(extracted_rooms)} room row(s)"
        )

        created_rooms = _auto_confirm_rooms(db, project.id, extracted_rooms)
        db.commit()
        for room in created_rooms:
            db.refresh(room)
        _log(f"Auto-confirmed {len(created_rooms)} room record(s)")

        created_doors = _auto_confirm_doors(db, extracted_doors, created_rooms)
        db.commit()
        for door in created_doors:
            db.refresh(door)
        _log(f"Auto-confirmed {len(created_doors)} door record(s)")

        if created_doors:
            _log(
                "Door-to-room assignment used round-robin across confirmed rooms "
                "(automation only; not for production review)."
            )

        clause_count = db.scalar(select(func.count()).select_from(RegulationClause))
        if not clause_count:
            _log(
                "Warning: no regulation clauses found. "
                "Run seed-regulations for citation-backed results."
            )

        report = build_compliance_report(project.id, db)
        _log(
            "Compliance engine finished: "
            f"{report.summary.passed} passed, {report.summary.failed} failed"
        )
        return report
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Upload interior_design.pdf to a fresh project, extract and "
            "auto-confirm door/room schedules, run compliance, and print the "
            "full report for manual sanity checking."
        )
    )
    parser.add_argument(
        "--pdf",
        type=Path,
        default=None,
        help="Path to the PDF file (defaults to data/raw/70-york-st/interior_design.pdf)",
    )
    parser.add_argument(
        "--door-page",
        type=int,
        default=1,
        help="1-based page number for door schedule extraction (default: 1)",
    )
    parser.add_argument(
        "--room-page",
        type=int,
        default=1,
        help="1-based page number for room schedule extraction (default: 1)",
    )
    parser.add_argument(
        "--project-prefix",
        default=DEFAULT_PROJECT_PREFIX,
        help=f"Prefix for the fresh project name (default: {DEFAULT_PROJECT_PREFIX})",
    )
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    report = run_full_pipeline_check(
        pdf_path=args.pdf,
        door_page=args.door_page,
        room_page=args.room_page,
        project_prefix=args.project_prefix,
    )
    _print_compliance_report(report)


if __name__ == "__main__":
    main()
