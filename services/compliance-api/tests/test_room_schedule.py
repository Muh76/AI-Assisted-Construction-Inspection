import pytest

from app.parsing.room_schedule import parse_room_schedule_table, parse_room_schedule_tables


@pytest.fixture
def sample_room_schedule_table() -> list[list[str]]:
    return [
        ["Room Name", "Occupancy Category", "Floor Area", "Occupant Load"],
        ["Reception", "B", "42.5", "5"],
        ["Office 101", "office", "18.6 sqm", "2"],
        ["Storage", "S-2", "12", "1"],
    ]


@pytest.fixture
def sample_unrelated_table() -> list[list[str]]:
    return [
        ["Door Number", "Width", "Fire Rating"],
        ["D-101", "860", "30 min"],
    ]


def test_parse_room_schedule_table(sample_room_schedule_table):
    rows = parse_room_schedule_table(sample_room_schedule_table)

    assert rows == [
        {
            "name": "Reception",
            "occupancy_category": "B",
            "floor_area": 42.5,
            "occupant_load": 5,
        },
        {
            "name": "Office 101",
            "occupancy_category": "office",
            "floor_area": 18.6,
            "occupant_load": 2,
        },
        {
            "name": "Storage",
            "occupancy_category": "S-2",
            "floor_area": 12.0,
            "occupant_load": 1,
        },
    ]


def test_parse_room_schedule_tables_ignores_unrelated_tables(
    sample_room_schedule_table,
    sample_unrelated_table,
):
    rows = parse_room_schedule_tables([sample_unrelated_table, sample_room_schedule_table])

    assert len(rows) == 3
    assert rows[0]["name"] == "Reception"


def test_parse_room_schedule_table_with_outdoor_air_headers():
    table = [
        ["Room", "Occupancy", "Area (sqm)", "Occupants"],
        ["Lobby", "Assembly", "120.0", "15"],
    ]

    rows = parse_room_schedule_table(table)

    assert rows == [
        {
            "name": "Lobby",
            "occupancy_category": "Assembly",
            "floor_area": 120.0,
            "occupant_load": 15,
        },
    ]


def test_parse_room_schedule_table_skips_invalid_rows():
    table = [
        ["Room Name", "Occupancy Category", "Floor Area", "Occupant Load"],
        ["", "B", "42", "5"],
        ["Office", "", "18.6", "2"],
        ["Corridor", "B", "n/a", "3"],
        ["Kitchen", "A-2", "25", "8"],
    ]

    rows = parse_room_schedule_table(table)

    assert rows == [
        {
            "name": "Kitchen",
            "occupancy_category": "A-2",
            "floor_area": 25.0,
            "occupant_load": 8,
        },
    ]
