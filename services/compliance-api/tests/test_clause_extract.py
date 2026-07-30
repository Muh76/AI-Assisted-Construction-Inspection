import pytest

from app.models import RegulationText
from app.parsing.clause_extract import extract_candidate_clauses


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
