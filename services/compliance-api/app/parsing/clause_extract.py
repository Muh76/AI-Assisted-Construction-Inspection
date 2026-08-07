import json
import re
from typing import Any

from app.ai.claude_client import call_claude
from app.models import RegulationText

SECTION_LINE_PATTERN = re.compile(
    r"^(?P<section>\d+(?:\.\d+)+)\s*(?P<rest>.*)$",
    re.MULTILINE,
)

CLAUSE_REFINEMENT_PROMPT = """You are reviewing a candidate building-code clause extracted by regex.

Section number: {section}
Page number: {page_number}
Candidate text:
---
{text}
---

Decide whether this text is a real regulation clause body (not a table-of-contents
entry, heading-only stub, or a mere cross-reference to another section).

Respond with JSON only (no markdown fences), using exactly this shape:
{{
  "is_regulation_clause": true,
  "title": "short clean title",
  "threshold_value": 860.0,
  "threshold_unit": "mm",
  "claude_confidence_note": "brief reason for the is_regulation_clause decision"
}}

Rules:
- is_regulation_clause must be true only if the text states a substantive requirement.
- title should be a concise clause title; use null if none can be determined.
- threshold_value and threshold_unit must be set only when a numeric threshold is
  clearly stated in the text; otherwise use null for both.
- claude_confidence_note must be a short explanation of why this is or is not a
  real regulation clause.
- Do not invent thresholds or titles that are not supported by the text.
"""


def _build_page_spans(
    text_pages: list[RegulationText],
) -> tuple[str, list[tuple[int, int, int]]]:
    """Return combined text and (page_number, start, end) spans."""
    sorted_pages = sorted(text_pages, key=lambda page: page.page_number)
    combined_parts: list[str] = []
    page_spans: list[tuple[int, int, int]] = []
    offset = 0

    for index, page in enumerate(sorted_pages):
        if index > 0:
            combined_parts.append("\n")
            offset += 1

        start = offset
        combined_parts.append(page.raw_text)
        offset += len(page.raw_text)
        page_spans.append((page.page_number, start, offset))

    return "".join(combined_parts), page_spans


def _page_number_for_offset(
    page_spans: list[tuple[int, int, int]],
    offset: int,
) -> int:
    for page_number, start, end in page_spans:
        if start <= offset < end:
            return page_number
    if page_spans:
        return page_spans[-1][0]
    return 1


def extract_candidate_clauses(
    text_pages: list[RegulationText],
) -> list[dict[str, Any]]:
    """Scan regulation text pages and split them into candidate clause sections."""
    if not text_pages:
        return []

    combined_text, page_spans = _build_page_spans(text_pages)
    matches = list(SECTION_LINE_PATTERN.finditer(combined_text))
    if not matches:
        return []

    clauses: list[dict[str, Any]] = []
    for index, match in enumerate(matches):
        section = match.group("section")
        text_start = match.start("rest")
        text_end = matches[index + 1].start() if index + 1 < len(matches) else len(combined_text)
        text = combined_text[text_start:text_end].strip()

        clauses.append(
            {
                "section": section,
                "text": text,
                "page_number": _page_number_for_offset(page_spans, match.start()),
            }
        )

    return clauses


def _parse_claude_json(raw_response: str) -> dict[str, Any]:
    cleaned = raw_response.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()

    data = json.loads(cleaned)
    if not isinstance(data, dict):
        raise ValueError("Claude response JSON must be an object")
    return data


def _normalize_refinement(data: dict[str, Any]) -> dict[str, Any]:
    is_clause = data.get("is_regulation_clause")
    if not isinstance(is_clause, bool):
        is_clause = False

    title = data.get("title")
    if title is not None:
        title = str(title).strip() or None

    threshold_value = data.get("threshold_value")
    if threshold_value is not None:
        try:
            threshold_value = float(threshold_value)
        except (TypeError, ValueError):
            threshold_value = None

    threshold_unit = data.get("threshold_unit")
    if threshold_unit is not None:
        threshold_unit = str(threshold_unit).strip() or None

    if threshold_value is None:
        threshold_unit = None

    note = data.get("claude_confidence_note")
    if note is not None:
        note = str(note).strip() or None

    return {
        "is_regulation_clause": is_clause,
        "title": title,
        "threshold_value": threshold_value,
        "threshold_unit": threshold_unit,
        "claude_confidence_note": note,
    }


def refine_candidate_clauses(
    candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Refine regex candidates with Claude (JSON-only), keeping the regex pass intact."""
    refined: list[dict[str, Any]] = []

    for candidate in candidates:
        section = str(candidate.get("section", "")).strip()
        text = str(candidate.get("text", "")).strip()
        page_number = candidate.get("page_number")

        prompt = CLAUSE_REFINEMENT_PROMPT.format(
            section=section,
            page_number=page_number,
            text=text,
        )
        raw_response = call_claude(prompt)
        try:
            parsed = _normalize_refinement(_parse_claude_json(raw_response))
        except (json.JSONDecodeError, ValueError, TypeError):
            parsed = {
                "is_regulation_clause": False,
                "title": None,
                "threshold_value": None,
                "threshold_unit": None,
                "claude_confidence_note": "Claude response was not valid JSON",
            }

        refined.append(
            {
                "section": section,
                "text": text,
                "page_number": page_number,
                **parsed,
            }
        )

    return refined
