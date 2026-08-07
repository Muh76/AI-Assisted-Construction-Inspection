"""Upload a real drawing PDF and print raw door/room schedule extraction output."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pdfplumber
from sqlalchemy import select

from app.config import get_data_raw_dir, get_repo_root
from app.db import SessionLocal
from app.models import Drawing, DrawingType, Project
from app.parsing.door_schedule import extract_door_schedule
from app.parsing.room_schedule import extract_room_schedule
from scripts.seed_example import _get_or_create_seed_user

DEFAULT_PROJECT_NAME = "70 York St Extraction Validation"
DEFAULT_GROUND_TRUTH = "docs/validation/70-york-st-ground-truth.json"
DEFAULT_PDF_CANDIDATES = (
    "data/raw/70-york-st/interior_design.pdf",
    "data/raw/70-york-st/interior design.pdf",
)


@dataclass(frozen=True)
class CategoryAccuracyReport:
    matched_exactly: int
    missed_entirely: int
    field_wrong: int


@dataclass(frozen=True)
class AccuracyReport:
    doors: CategoryAccuracyReport
    rooms: CategoryAccuracyReport


def _resolve_pdf_path(explicit_path: Path | None) -> Path:
    if explicit_path is not None:
        if not explicit_path.is_file():
            raise FileNotFoundError(f"PDF not found at {explicit_path}")
        return explicit_path

    repo_root = get_repo_root()
    for relative_path in DEFAULT_PDF_CANDIDATES:
        candidate = repo_root / relative_path
        if candidate.is_file():
            return candidate

    searched = ", ".join(str(repo_root / path) for path in DEFAULT_PDF_CANDIDATES)
    raise FileNotFoundError(
        "Could not find interior_design.pdf. Checked: "
        f"{searched}. Pass --pdf, --doors-pdf, or --rooms-pdf to specify the file path."
    )


def _resolve_ground_truth_path(explicit_path: Path | None) -> Path:
    if explicit_path is not None:
        if not explicit_path.is_file():
            raise FileNotFoundError(f"Ground truth file not found at {explicit_path}")
        return explicit_path

    path = get_repo_root() / DEFAULT_GROUND_TRUTH
    if not path.is_file():
        raise FileNotFoundError(f"Ground truth file not found at {path}")
    return path


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _normalize_optional_text(value: Any) -> str | None:
    normalized = _normalize_text(value)
    return normalized or None


def _normalize_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _normalize_int(value: Any) -> int | None:
    number = _normalize_float(value)
    if number is None:
        return None
    return int(round(number))


def _is_placeholder_door(record: dict[str, Any]) -> bool:
    return not _normalize_text(record.get("door_no"))


def _is_placeholder_room(record: dict[str, Any]) -> bool:
    return not _normalize_text(record.get("name")) and not _normalize_text(
        record.get("room_no")
    )


def _door_key(record: dict[str, Any], *, from_ground_truth: bool) -> str:
    if from_ground_truth:
        return _normalize_text(record.get("door_no")).upper()
    return _normalize_text(record.get("door_number")).upper()


def _room_key(record: dict[str, Any]) -> str:
    name = _normalize_text(record.get("name"))
    if name:
        return name.casefold()
    return _normalize_text(record.get("room_no")).casefold()


def _normalize_ground_truth_door(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "door_no": _normalize_text(record.get("door_no")),
        "clear_width_mm": _normalize_float(record.get("clear_width_mm")),
        "fire_rating": _normalize_optional_text(record.get("fire_rating")),
    }


def _normalize_extracted_door(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "door_no": _normalize_text(record.get("door_number")),
        "clear_width_mm": _normalize_float(record.get("width")),
        "fire_rating": _normalize_optional_text(record.get("fire_rating")),
    }


def _normalize_ground_truth_room(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "room_no": _normalize_text(record.get("room_no")),
        "name": _normalize_text(record.get("name")),
        "occupancy_category": _normalize_text(record.get("occupancy_category")),
        "floor_area": _normalize_float(record.get("floor_area")),
        "occupant_load": _normalize_int(record.get("occupant_load")),
    }


def _normalize_extracted_room(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "room_no": "",
        "name": _normalize_text(record.get("name")),
        "occupancy_category": _normalize_text(record.get("occupancy_category")),
        "floor_area": _normalize_float(record.get("floor_area")),
        "occupant_load": _normalize_int(record.get("occupant_load")),
    }


def _fields_match(expected: Any, actual: Any) -> bool:
    if isinstance(expected, float) or isinstance(actual, float):
        if expected is None or actual is None:
            return expected is None and actual is None
        return float(expected) == float(actual)
    return expected == actual


def _compare_category(
    ground_truth_records: list[dict[str, Any]],
    extracted_records: list[dict[str, Any]],
    *,
    is_placeholder,
    ground_truth_key,
    extracted_key,
    normalize_ground_truth,
    normalize_extracted,
    comparable_fields: tuple[str, ...],
) -> CategoryAccuracyReport:
    matched_exactly = 0
    missed_entirely = 0
    field_wrong = 0

    extracted_by_key = {
        extracted_key(record): normalize_extracted(record)
        for record in extracted_records
        if extracted_key(record)
    }

    for ground_truth_record in ground_truth_records:
        if is_placeholder(ground_truth_record):
            continue

        key = ground_truth_key(ground_truth_record, from_ground_truth=True)
        expected = normalize_ground_truth(ground_truth_record)
        actual = extracted_by_key.get(key)

        if actual is None:
            missed_entirely += 1
            continue

        if all(
            _fields_match(expected[field], actual[field]) for field in comparable_fields
        ):
            matched_exactly += 1
        else:
            field_wrong += 1

    return CategoryAccuracyReport(
        matched_exactly=matched_exactly,
        missed_entirely=missed_entirely,
        field_wrong=field_wrong,
    )


def compare_against_ground_truth(
    ground_truth: dict[str, Any],
    extracted_doors: list[dict[str, Any]],
    extracted_rooms: list[dict[str, Any]],
) -> AccuracyReport:
    door_fields = ("door_no", "clear_width_mm", "fire_rating")
    room_fields = (
        "name",
        "occupancy_category",
        "floor_area",
        "occupant_load",
    )

    return AccuracyReport(
        doors=_compare_category(
            ground_truth.get("doors", []),
            extracted_doors,
            is_placeholder=_is_placeholder_door,
            ground_truth_key=_door_key,
            extracted_key=lambda record: _door_key(record, from_ground_truth=False),
            normalize_ground_truth=_normalize_ground_truth_door,
            normalize_extracted=_normalize_extracted_door,
            comparable_fields=door_fields,
        ),
        rooms=_compare_category(
            ground_truth.get("rooms", []),
            extracted_rooms,
            is_placeholder=_is_placeholder_room,
            ground_truth_key=lambda record, from_ground_truth=True: _room_key(record),
            extracted_key=lambda record: _room_key(record),
            normalize_ground_truth=_normalize_ground_truth_room,
            normalize_extracted=_normalize_extracted_room,
            comparable_fields=room_fields,
        ),
    )


def load_ground_truth(path: Path | None = None) -> dict[str, Any]:
    ground_truth_path = _resolve_ground_truth_path(path)
    return json.loads(ground_truth_path.read_text(encoding="utf-8"))


def print_accuracy_report(report: AccuracyReport, *, stream=None) -> None:
    if stream is None:
        stream = sys.stderr

    print("Accuracy report", file=stream)
    print("=" * 40, file=stream)

    for label, category in (("Doors", report.doors), ("Rooms", report.rooms)):
        print(label, file=stream)
        print(f"  matched exactly:   {category.matched_exactly}", file=stream)
        print(f"  missed entirely:   {category.missed_entirely}", file=stream)
        print(f"  field wrong:       {category.field_wrong}", file=stream)
        print(file=stream)


def _get_or_create_validation_project(db, project_name: str, owner) -> Project:
    project = db.scalar(select(Project).where(Project.name == project_name))
    if project is not None:
        return project

    project = Project(name=project_name, owner_id=owner.id)
    db.add(project)
    db.flush()
    return project


def _upload_drawing(
    db,
    project: Project,
    pdf_path: Path,
    *,
    label: str = "drawing",
) -> Drawing:
    upload_date = datetime.now(UTC).replace(tzinfo=None)
    timestamp = upload_date.strftime("%Y%m%d_%H%M%S")
    saved_filename = f"project-{project.id}-{timestamp}-{label}.pdf"

    raw_dir = get_data_raw_dir()
    raw_dir.mkdir(parents=True, exist_ok=True)
    destination = raw_dir / saved_filename
    shutil.copy2(pdf_path, destination)

    drawing = Drawing(
        project_id=project.id,
        type=DrawingType.ARCHITECTURAL,
        file_path=f"data/raw/{saved_filename}",
        upload_date=upload_date,
    )
    db.add(drawing)
    db.flush()
    return drawing


def _count_pdf_pages(pdf_path: Path) -> int:
    with pdfplumber.open(pdf_path) as pdf:
        return len(pdf.pages)


def validate_extraction(
    pdf_path: Path | None = None,
    doors_pdf: Path | None = None,
    rooms_pdf: Path | None = None,
    door_page: int = 1,
    room_page: int = 1,
    project_name: str = DEFAULT_PROJECT_NAME,
) -> dict:
    # --doors-pdf / --rooms-pdf win when set; otherwise fall back to --pdf,
    # then DEFAULT_PDF_CANDIDATES (same as a single-file --pdf run).
    doors_source_pdf = _resolve_pdf_path(doors_pdf if doors_pdf is not None else pdf_path)
    rooms_source_pdf = _resolve_pdf_path(rooms_pdf if rooms_pdf is not None else pdf_path)
    doors_page_count = _count_pdf_pages(doors_source_pdf)
    rooms_page_count = _count_pdf_pages(rooms_source_pdf)

    print(
        f"Using doors PDF: {doors_source_pdf} ({doors_page_count} pages)",
        file=sys.stderr,
    )
    print(
        f"Using rooms PDF: {rooms_source_pdf} ({rooms_page_count} pages)",
        file=sys.stderr,
    )

    db = SessionLocal()
    try:
        owner = _get_or_create_seed_user(db)
        project = _get_or_create_validation_project(db, project_name, owner)
        doors_drawing = _upload_drawing(db, project, doors_source_pdf, label="doors")
        rooms_drawing = _upload_drawing(db, project, rooms_source_pdf, label="rooms")
        db.commit()
        db.refresh(doors_drawing)
        db.refresh(rooms_drawing)

        print(
            f"Uploaded doors drawing id={doors_drawing.id} and rooms drawing "
            f"id={rooms_drawing.id} for project id={project.id}",
            file=sys.stderr,
        )

        doors = extract_door_schedule(doors_drawing.id, door_page, db)
        rooms = extract_room_schedule(rooms_drawing.id, room_page, db)

        result = {
            "project_id": project.id,
            "doors_drawing_id": doors_drawing.id,
            "rooms_drawing_id": rooms_drawing.id,
            "doors_source_pdf": str(doors_source_pdf),
            "rooms_source_pdf": str(rooms_source_pdf),
            "doors_stored_pdf": doors_drawing.file_path,
            "rooms_stored_pdf": rooms_drawing.file_path,
            "doors_page_count": doors_page_count,
            "rooms_page_count": rooms_page_count,
            "door_page": door_page,
            "room_page": room_page,
            "doors": doors,
            "rooms": rooms,
        }

        # Preserve single-file --pdf response keys when both sources match.
        if doors_source_pdf == rooms_source_pdf:
            result["drawing_id"] = doors_drawing.id
            result["source_pdf"] = str(doors_source_pdf)
            result["stored_pdf"] = doors_drawing.file_path
            result["page_count"] = doors_page_count

        return result
    finally:
        db.close()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Upload drawing PDF(s), print raw door/room schedule extraction "
            "output as JSON, and compare against ground truth."
        )
    )
    parser.add_argument(
        "--pdf",
        type=Path,
        default=None,
        help=(
            "Single PDF used for both door and room extraction when "
            "--doors-pdf / --rooms-pdf are omitted "
            "(defaults to data/raw/70-york-st/interior_design.pdf)"
        ),
    )
    parser.add_argument(
        "--doors-pdf",
        type=Path,
        default=None,
        help=(
            "PDF for door schedule extraction "
            "(falls back to --pdf, then DEFAULT_PDF_CANDIDATES)"
        ),
    )
    parser.add_argument(
        "--rooms-pdf",
        type=Path,
        default=None,
        help=(
            "PDF for room schedule extraction "
            "(falls back to --pdf, then DEFAULT_PDF_CANDIDATES)"
        ),
    )
    parser.add_argument(
        "--ground-truth",
        type=Path,
        default=None,
        help=f"Ground truth JSON path (default: {DEFAULT_GROUND_TRUTH})",
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
        "--project-name",
        default=DEFAULT_PROJECT_NAME,
        help=f"Validation project name (default: {DEFAULT_PROJECT_NAME})",
    )
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    result = validate_extraction(
        pdf_path=args.pdf,
        doors_pdf=args.doors_pdf,
        rooms_pdf=args.rooms_pdf,
        door_page=args.door_page,
        room_page=args.room_page,
        project_name=args.project_name,
    )
    ground_truth = load_ground_truth(args.ground_truth)
    accuracy = compare_against_ground_truth(
        ground_truth,
        result["doors"],
        result["rooms"],
    )

    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    print_accuracy_report(accuracy)


if __name__ == "__main__":
    main()
