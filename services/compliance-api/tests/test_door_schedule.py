import pytest

from app.parsing.door_schedule import parse_door_schedule_table, parse_door_schedule_tables


@pytest.fixture
def sample_door_schedule_table() -> list[list[str]]:
    return [
        ["Door Number", "Width", "Fire Rating"],
        ["D-101", "860", "30 min"],
        ["D-102", "920 mm", "45 min"],
        ["D-103", "750", ""],
    ]


@pytest.fixture
def sample_unrelated_table() -> list[list[str]]:
    return [
        ["Room", "Area", "Occupancy"],
        ["Reception", "42", "B"],
    ]


def test_parse_door_schedule_table(sample_door_schedule_table):
    rows = parse_door_schedule_table(sample_door_schedule_table)

    assert rows == [
        {"door_number": "D-101", "width": 860.0, "fire_rating": "30 min"},
        {"door_number": "D-102", "width": 920.0, "fire_rating": "45 min"},
        {"door_number": "D-103", "width": 750.0, "fire_rating": None},
    ]


def test_parse_door_schedule_tables_ignores_unrelated_tables(
    sample_door_schedule_table,
    sample_unrelated_table,
):
    rows = parse_door_schedule_tables([sample_unrelated_table, sample_door_schedule_table])

    assert len(rows) == 3
    assert rows[0]["door_number"] == "D-101"
    assert rows[1]["door_number"] == "D-102"
    assert rows[2]["door_number"] == "D-103"


def test_parse_door_schedule_table_with_alternate_headers():
    table = [
        ["Door Mark", "Clear Width", "Rating"],
        ["101A", "860 mm", "30 min"],
    ]

    rows = parse_door_schedule_table(table)

    assert rows == [
        {"door_number": "101A", "width": 860.0, "fire_rating": "30 min"},
    ]


def test_parse_door_schedule_table_skips_invalid_rows():
    table = [
        ["Door Number", "Width", "Fire Rating"],
        ["", "860", "30 min"],
        ["D-200", "n/a", "30 min"],
        ["D-201", "800", "60 min"],
    ]

    rows = parse_door_schedule_table(table)

    assert rows == [
        {"door_number": "D-201", "width": 800.0, "fire_rating": "60 min"},
    ]
