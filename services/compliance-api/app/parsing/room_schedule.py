import json
import re
from pathlib import Path
from typing import Any

import pdfplumber
from sqlalchemy.orm import Session

from app.ai.claude_client import call_claude
from app.config import get_repo_root
from app.models import Drawing
from app.parsing.page_image import render_drawing_page
from app.parsing.raw_extract import _resolve_drawing_path

ROOM_NAME_HEADERS = {
    "room",
    "room name",
    "space",
    "space name",
    "name",
    "area name",
}
OCCUPANCY_CATEGORY_HEADERS = {
    "occupancy category",
    "occupancy",
    "category",
    "occ category",
    "use",
    "occupancy type",
    "occ. category",
}
FLOOR_AREA_HEADERS = {
    "floor area",
    "area",
    "floor area (sqm)",
    "floor area (m2)",
    "area (sqm)",
    "area (m2)",
    "sqm",
    "gross area",
    "net area",
}
OCCUPANT_LOAD_HEADERS = {
    "occupant load",
    "occupants",
    "ol",
    "load",
    "no. of occupants",
    "number of occupants",
    "occ load",
}

_NUMBER_PATTERN = re.compile(r"[\d.]+")

ROOM_VISION_PROMPT = """You are analyzing an architectural drawing page that may contain
a room schedule, zone schedule, or similar table of spaces.

Read the room/zone table from the image and return JSON only (no markdown fences)
with this exact shape:
{
  "rooms": [
    {
      "name": "Reception",
      "occupancy_category": "Office - Reception",
      "floor_area": 16.54,
      "occupant_load": 0
    }
  ]
}

Rules:
- Only include rows you can read with high confidence.
- name is the room or zone name/label.
- occupancy_category is the occupancy / use category text as shown.
- floor_area must be numeric (square metres when available).
- occupant_load must be an integer occupant count.
- If no confident room rows are found, return {"rooms": []}.
"""


def _normalize_cell(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _normalize_header(value: Any) -> str:
    return _normalize_cell(value).lower()


def _parse_number(value: str) -> float | None:
    if not value:
        return None
    match = _NUMBER_PATTERN.search(value.replace(",", ""))
    if match is None:
        return None
    return float(match.group())


def _parse_int(value: str) -> int | None:
    number = _parse_number(value)
    if number is None:
        return None
    return int(round(number))


def _find_column_indexes(header_row: list[Any]) -> dict[str, int] | None:
    normalized_headers = [_normalize_header(cell) for cell in header_row]
    indexes: dict[str, int] = {}

    for index, header in enumerate(normalized_headers):
        if header in ROOM_NAME_HEADERS:
            indexes["name"] = index
        elif header in OCCUPANCY_CATEGORY_HEADERS:
            indexes["occupancy_category"] = index
        elif header in FLOOR_AREA_HEADERS:
            indexes["floor_area"] = index
        elif header in OCCUPANT_LOAD_HEADERS:
            indexes["occupant_load"] = index

    required = {"name", "occupancy_category", "floor_area", "occupant_load"}
    if not required.issubset(indexes):
        return None

    return indexes


def parse_room_schedule_table(table: list[list[Any]]) -> list[dict[str, Any]]:
    if not table:
        return []

    column_indexes = _find_column_indexes(table[0])
    if column_indexes is None:
        return []

    rows: list[dict[str, Any]] = []
    for raw_row in table[1:]:
        if not raw_row:
            continue

        name = _normalize_cell(
            raw_row[column_indexes["name"]]
            if column_indexes["name"] < len(raw_row)
            else None
        )
        if not name or _normalize_header(name) in ROOM_NAME_HEADERS:
            continue

        occupancy_category = _normalize_cell(
            raw_row[column_indexes["occupancy_category"]]
            if column_indexes["occupancy_category"] < len(raw_row)
            else None
        )
        if not occupancy_category:
            continue

        floor_area_value = _normalize_cell(
            raw_row[column_indexes["floor_area"]]
            if column_indexes["floor_area"] < len(raw_row)
            else None
        )
        floor_area = _parse_number(floor_area_value)
        if floor_area is None:
            continue

        occupant_load_value = _normalize_cell(
            raw_row[column_indexes["occupant_load"]]
            if column_indexes["occupant_load"] < len(raw_row)
            else None
        )
        occupant_load = _parse_int(occupant_load_value)
        if occupant_load is None:
            continue

        rows.append(
            {
                "name": name,
                "occupancy_category": occupancy_category,
                "floor_area": floor_area,
                "occupant_load": occupant_load,
            }
        )

    return rows


def parse_room_schedule_tables(tables: list[list[list[Any]]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for table in tables:
        rows.extend(parse_room_schedule_table(table))
    return rows


def extract_room_schedule_from_page(page: Any) -> list[dict[str, Any]]:
    tables = page.extract_tables() or []
    return parse_room_schedule_tables(tables)


def _strip_markdown_fences(content: str) -> str:
    cleaned = content.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    return cleaned


def _normalize_vision_rooms(raw_rooms: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_rooms, list):
        return []

    normalized: list[dict[str, Any]] = []
    for item in raw_rooms:
        if not isinstance(item, dict):
            continue

        name = item.get("name")
        occupancy_category = item.get("occupancy_category")
        floor_area = item.get("floor_area")
        occupant_load = item.get("occupant_load")

        if not isinstance(name, str) or not name.strip():
            continue
        if not isinstance(occupancy_category, str) or not occupancy_category.strip():
            continue
        if not isinstance(floor_area, (int, float)):
            continue
        if isinstance(occupant_load, bool) or not isinstance(occupant_load, (int, float)):
            continue

        normalized.append(
            {
                "name": name.strip(),
                "occupancy_category": occupancy_category.strip(),
                "floor_area": float(floor_area),
                "occupant_load": int(round(float(occupant_load))),
            }
        )

    return normalized


def _parse_vision_response(content: str) -> list[dict[str, Any]]:
    data = json.loads(_strip_markdown_fences(content))
    if isinstance(data, dict):
        rooms = data.get("rooms", [])
    elif isinstance(data, list):
        rooms = data
    else:
        rooms = []
    return _normalize_vision_rooms(rooms)


def _request_room_schedule_from_image(image_path: Path) -> list[dict[str, Any]]:
    image_bytes = image_path.read_bytes()
    content = call_claude(ROOM_VISION_PROMPT, image_bytes=image_bytes)
    if not content:
        return []
    return _parse_vision_response(content)


def _extract_room_schedule_via_vision(
    drawing_id: int,
    page_number: int,
    db: Session,
) -> list[dict[str, Any]]:
    relative_image_path = render_drawing_page(drawing_id, page_number, db)
    absolute_image_path = get_repo_root() / relative_image_path
    return _request_room_schedule_from_image(absolute_image_path)


def extract_room_schedule(
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
        rows = extract_room_schedule_from_page(page)

    if rows:
        return rows

    return _extract_room_schedule_via_vision(drawing_id, page_number, db)
