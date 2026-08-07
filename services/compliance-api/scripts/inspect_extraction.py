"""Preview door/room schedule extraction for a drawing page (no DB writes)."""

from __future__ import annotations

import argparse
import sys
from typing import Any

from app.db import SessionLocal
from app.models import Drawing
from app.parsing.door_schedule import extract_door_schedule
from app.parsing.room_schedule import extract_room_schedule


def _print_section(title: str) -> None:
    print()
    print(title)
    print("=" * len(title))


def _format_value(value: Any) -> str:
    if value is None:
        return "—"
    return str(value)


def _print_table(headers: list[str], rows: list[list[Any]]) -> None:
    if not rows:
        print("(no candidates)")
        return

    string_rows = [[_format_value(cell) for cell in row] for row in rows]
    widths = [len(header) for header in headers]
    for row in string_rows:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(cell))

    header_line = " | ".join(
        header.ljust(widths[index]) for index, header in enumerate(headers)
    )
    divider = "-+-".join("-" * width for width in widths)
    print(header_line)
    print(divider)
    for row in string_rows:
        print(
            " | ".join(cell.ljust(widths[index]) for index, cell in enumerate(row))
        )


def inspect_extraction(drawing_id: int, page_number: int) -> None:
    db = SessionLocal()
    try:
        drawing = db.get(Drawing, drawing_id)
        if drawing is None:
            raise SystemExit(f"Drawing {drawing_id} not found")

        print(f"Drawing ID:  {drawing.id}")
        print(f"Project ID:  {drawing.project_id}")
        print(f"Type:        {drawing.type.value}")
        print(f"File:        {drawing.file_path}")
        print(f"Page:        {page_number}")
        print("Mode:        preview only (nothing saved)")

        doors = extract_door_schedule(drawing_id, page_number, db)
        rooms = extract_room_schedule(drawing_id, page_number, db)

        _print_section(f"Door schedule candidates ({len(doors)})")
        _print_table(
            ["#", "door_number", "width", "fire_rating"],
            [
                [
                    index,
                    row.get("door_number"),
                    row.get("width"),
                    row.get("fire_rating"),
                ]
                for index, row in enumerate(doors, start=1)
            ],
        )

        _print_section(f"Room schedule candidates ({len(rooms)})")
        _print_table(
            ["#", "name", "occupancy_category", "floor_area", "occupant_load"],
            [
                [
                    index,
                    row.get("name"),
                    row.get("occupancy_category"),
                    row.get("floor_area"),
                    row.get("occupant_load"),
                ]
                for index, row in enumerate(rooms, start=1)
            ],
        )

        print()
        print(
            "Compare these rows against the PDF page side by side. "
            "Nothing was written to the database."
        )
    except (FileNotFoundError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc
    finally:
        db.close()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run door and room schedule preview extraction for one drawing page "
            "and print candidate rows. Does not confirm or save anything."
        )
    )
    parser.add_argument("drawing_id", type=int, help="Drawing ID in the database")
    parser.add_argument(
        "page",
        type=int,
        help="1-based PDF page number to inspect",
    )
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    if args.page < 1:
        print("page must be at least 1", file=sys.stderr)
        raise SystemExit(2)
    inspect_extraction(args.drawing_id, args.page)


if __name__ == "__main__":
    main()
