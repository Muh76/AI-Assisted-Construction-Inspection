import json
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.ai.claude_client import call_claude
from app.config import get_repo_root
from app.parsing.page_image import render_drawing_page

CORRIDOR_VISION_PROMPT = """You are analyzing an architectural floor plan page.
Identify corridor width dimension callouts visible on this drawing.

Return JSON only (no markdown fences) with this exact shape:
{
  "callouts": [
    {
      "label": "short identifier for the corridor or dimension line",
      "width_mm": 1100,
      "approximate_location": "brief description of where on the page"
    }
  ]
}

Rules:
- Only include corridor width dimensions you can read with high confidence.
- Omit any callout that is ambiguous, partially obscured, or unclear.
- width_mm must be the numeric width in millimeters.
- If no confident callouts are found, return {"callouts": []}.
"""


def _normalize_callouts(raw_callouts: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_callouts, list):
        return []

    normalized: list[dict[str, Any]] = []
    for item in raw_callouts:
        if not isinstance(item, dict):
            continue

        label = item.get("label")
        width_mm = item.get("width_mm")
        approximate_location = item.get("approximate_location")
        if not isinstance(label, str) or not label.strip():
            continue
        if not isinstance(width_mm, (int, float)):
            continue
        if not isinstance(approximate_location, str) or not approximate_location.strip():
            continue

        normalized.append(
            {
                "label": label.strip(),
                "width_mm": float(width_mm),
                "approximate_location": approximate_location.strip(),
            }
        )

    return normalized


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


def _parse_llm_response(content: str) -> list[dict[str, Any]]:
    data = json.loads(_strip_markdown_fences(content))
    if isinstance(data, dict):
        callouts = data.get("callouts", [])
    elif isinstance(data, list):
        callouts = data
    else:
        callouts = []
    return _normalize_callouts(callouts)


def _request_corridor_callouts(image_path: Path) -> list[dict[str, Any]]:
    image_bytes = image_path.read_bytes()
    content = call_claude(CORRIDOR_VISION_PROMPT, image_bytes=image_bytes)
    if not content:
        return []
    return _parse_llm_response(content)


def parse_corridor_width_callouts(
    drawing_id: int,
    page_number: int,
    db: Session,
) -> tuple[str, list[dict[str, Any]]]:
    """Render a drawing page and ask Claude for corridor width callouts."""
    image_path = render_drawing_page(drawing_id, page_number, db)
    absolute_path = get_repo_root() / image_path
    callouts = _request_corridor_callouts(absolute_path)
    return image_path, callouts
