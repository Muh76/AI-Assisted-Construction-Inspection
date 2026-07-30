import re
from typing import Any

import pdfplumber
from sqlalchemy.orm import Session

from app.models import Drawing
from app.parsing.raw_extract import _resolve_drawing_path

DOOR_NUMBER_HEADERS = {
    "door number",
    "door no",
    "door no.",
    "door #",
    "mark",
    "door mark",
}
WIDTH_HEADERS = {
    "width",
    "clear width",
    "door width",
    "width (mm)",
    "width mm",
}
FIRE_RATING_HEADERS = {
    "fire rating",
    "rating",
    "fire rating (min)",
    "fire rating min",
}

_WIDTH_PATTERN = re.compile(r"[\d.]+")


def _normalize_cell(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _normalize_header(value: Any) -> str:
    return _normalize_cell(value).lower()


def _parse_width(value: str) -> float | None:
    if not value:
        return None
    match = _WIDTH_PATTERN.search(value.replace(",", ""))
    if match is None:
        return None
    return float(match.group())


def _find_column_indexes(header_row: list[Any]) -> dict[str, int] | None:
    normalized_headers = [_normalize_header(cell) for cell in header_row]
    indexes: dict[str, int] = {}

    for index, header in enumerate(normalized_headers):
        if header in DOOR_NUMBER_HEADERS:
            indexes["door_number"] = index
        elif header in WIDTH_HEADERS:
            indexes["width"] = index
        elif header in FIRE_RATING_HEADERS:
            indexes["fire_rating"] = index

    if "door_number" not in indexes or "width" not in indexes:
        return None

    return indexes


def parse_door_schedule_table(table: list[list[Any]]) -> list[dict[str, Any]]:
    if not table:
        return []

    column_indexes = _find_column_indexes(table[0])
    if column_indexes is None:
        return []

    rows: list[dict[str, Any]] = []
    for raw_row in table[1:]:
        if not raw_row:
            continue

        door_number = _normalize_cell(
            raw_row[column_indexes["door_number"]]
            if column_indexes["door_number"] < len(raw_row)
            else None
        )
        if not door_number or _normalize_header(door_number) in DOOR_NUMBER_HEADERS:
            continue

        width_value = _normalize_cell(
            raw_row[column_indexes["width"]]
            if column_indexes["width"] < len(raw_row)
            else None
        )
        width = _parse_width(width_value)
        if width is None:
            continue

        fire_rating: str | None = None
        if "fire_rating" in column_indexes and column_indexes["fire_rating"] < len(raw_row):
            fire_rating_value = _normalize_cell(raw_row[column_indexes["fire_rating"]])
            fire_rating = fire_rating_value or None

        rows.append(
            {
                "door_number": door_number,
                "width": width,
                "fire_rating": fire_rating,
            }
        )

    return rows


def parse_door_schedule_tables(tables: list[list[list[Any]]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for table in tables:
        rows.extend(parse_door_schedule_table(table))
    return rows


def extract_door_schedule_from_page(page: Any) -> list[dict[str, Any]]:
    tables = page.extract_tables() or []
    return parse_door_schedule_tables(tables)


def extract_door_schedule(
    drawing_id: int,
    page_number: int,
    db: Session,
) -> list[dict[str, Any]]:
    drawing = db.get(Drawing, drawing_id)
    if drawing is None:
        raise ValueError(f"Drawing {drawing_id} not found")

    pdf_path = _resolve_drawing_path(drawing)
    if not pdf_path.is_file():
        raise FileNotFoundError(f"Drawing PDF not found at {pdf_path}")

    with pdfplumber.open(pdf_path) as pdf:
        if page_number < 1 or page_number > len(pdf.pages):
            raise ValueError(
                f"Page number {page_number} is out of range for drawing {drawing_id}"
            )
        page = pdf.pages[page_number - 1]
        return extract_door_schedule_from_page(page)
