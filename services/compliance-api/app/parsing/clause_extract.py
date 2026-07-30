import re
from typing import Any

from app.models import RegulationText

SECTION_LINE_PATTERN = re.compile(
    r"^(?P<section>\d+(?:\.\d+)+)\s*(?P<rest>.*)$",
    re.MULTILINE,
)


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
