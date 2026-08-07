import json
from unittest.mock import patch

import pytest

from app.models import RegulationText
from app.parsing.clause_extract import (
    extract_candidate_clauses,
    refine_candidate_clauses,
)


@pytest.fixture
def sample_regulation_text_pages() -> list[RegulationText]:
    return [
        RegulationText(
            document_id=1,
            page_number=1,
            raw_text=(
                "3.4.3.5 Door width\n"
                "Doors shall have a minimum clear width of 860 mm.\n"
                "\n"
                "3.4.3.6 Door hardware\n"
                "Hardware shall comply with Section 3.4.3.5.\n"
                "See also 3.4.7.1 for exit requirements."
            ),
        ),
        RegulationText(
            document_id=1,
            page_number=2,
            raw_text=(
                "3.3.2.4 Corridor width\n"
                "Corridors shall be not less than\n"
                "1100 mm in clear width.\n"
                "\n"
                "3.3.2.5 Corridor length\n"
                "Maximum unobstructed length applies."
            ),
        ),
    ]


def test_extract_candidate_clauses_from_sample_text(sample_regulation_text_pages):
    clauses = extract_candidate_clauses(sample_regulation_text_pages)

    assert len(clauses) == 4
    assert [clause["section"] for clause in clauses] == [
        "3.4.3.5",
        "3.4.3.6",
        "3.3.2.4",
        "3.3.2.5",
    ]

    first_clause = clauses[0]
    assert first_clause["page_number"] == 1
    assert first_clause["text"] == (
        "Door width\nDoors shall have a minimum clear width of 860 mm."
    )

    second_clause = clauses[1]
    assert second_clause["page_number"] == 1
    assert second_clause["text"] == (
        "Door hardware\n"
        "Hardware shall comply with Section 3.4.3.5.\n"
        "See also 3.4.7.1 for exit requirements."
    )

    third_clause = clauses[2]
    assert third_clause["page_number"] == 2
    assert third_clause["text"] == (
        "Corridor width\n"
        "Corridors shall be not less than\n"
        "1100 mm in clear width."
    )

    fourth_clause = clauses[3]
    assert fourth_clause["page_number"] == 2
    assert fourth_clause["text"] == (
        "Corridor length\nMaximum unobstructed length applies."
    )


def test_extract_candidate_clauses_ignores_non_line_start_sections():
    text_pages = [
        RegulationText(
            document_id=1,
            page_number=1,
            raw_text="See also 3.4.3.5 for door width requirements.",
        )
    ]

    assert extract_candidate_clauses(text_pages) == []


def test_extract_candidate_clauses_returns_empty_for_no_pages():
    assert extract_candidate_clauses([]) == []


def test_refine_candidate_clauses_uses_claude_json(sample_regulation_text_pages):
    candidates = extract_candidate_clauses(sample_regulation_text_pages)[:2]

    responses = [
        json.dumps(
            {
                "is_regulation_clause": True,
                "title": "Door width",
                "threshold_value": 860,
                "threshold_unit": "mm",
                "claude_confidence_note": "States a clear minimum clear-width requirement.",
            }
        ),
        json.dumps(
            {
                "is_regulation_clause": False,
                "title": None,
                "threshold_value": None,
                "threshold_unit": None,
                "claude_confidence_note": "Mostly a cross-reference, not a substantive rule.",
            }
        ),
    ]

    with patch(
        "app.parsing.clause_extract.call_claude",
        side_effect=responses,
    ) as mock_claude:
        refined = refine_candidate_clauses(candidates)

    assert mock_claude.call_count == 2
    assert refined[0] == {
        "section": "3.4.3.5",
        "text": candidates[0]["text"],
        "page_number": 1,
        "is_regulation_clause": True,
        "title": "Door width",
        "threshold_value": 860.0,
        "threshold_unit": "mm",
        "claude_confidence_note": "States a clear minimum clear-width requirement.",
    }
    assert refined[1]["is_regulation_clause"] is False
    assert refined[1]["title"] is None
    assert refined[1]["threshold_value"] is None
    assert refined[1]["claude_confidence_note"] == (
        "Mostly a cross-reference, not a substantive rule."
    )
    assert "Respond with JSON only" in mock_claude.call_args_list[0].args[0]
    assert "claude_confidence_note" in mock_claude.call_args_list[0].args[0]


def test_refine_candidate_clauses_handles_invalid_json():
    candidates = [
        {
            "section": "3.1.1.1",
            "text": "Not useful",
            "page_number": 1,
        }
    ]

    with patch(
        "app.parsing.clause_extract.call_claude",
        return_value="not-json",
    ):
        refined = refine_candidate_clauses(candidates)

    assert refined == [
        {
            "section": "3.1.1.1",
            "text": "Not useful",
            "page_number": 1,
            "is_regulation_clause": False,
            "title": None,
            "threshold_value": None,
            "threshold_unit": None,
            "claude_confidence_note": "Claude response was not valid JSON",
        }
    ]
