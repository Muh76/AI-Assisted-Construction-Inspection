import json
from datetime import UTC, datetime
from io import BytesIO

import pytest
from PIL import Image
from reportlab.pdfgen import canvas

from app.models import Drawing, DrawingType, Project, User
from app.parsing.room_schedule import (
    _parse_vision_response,
    extract_room_schedule,
    parse_room_schedule_table,
    parse_room_schedule_tables,
)


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


def test_parse_vision_response_normalizes_rooms():
    content = json.dumps(
        {
            "rooms": [
                {
                    "name": "Reception",
                    "occupancy_category": "Office - Reception",
                    "floor_area": 16.54,
                    "occupant_load": 0,
                },
                {
                    "name": "",
                    "occupancy_category": "Office",
                    "floor_area": 10.0,
                    "occupant_load": 1,
                },
                {
                    "name": "Office",
                    "occupancy_category": "Office - Office Space",
                    "floor_area": "bad",
                    "occupant_load": 1,
                },
            ]
        }
    )

    rooms = _parse_vision_response(content)

    assert rooms == [
        {
            "name": "Reception",
            "occupancy_category": "Office - Reception",
            "floor_area": 16.54,
            "occupant_load": 0,
        }
    ]


def _make_test_pdf() -> bytes:
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer)
    pdf.drawString(72, 720, "Room schedule page without extractable tables")
    pdf.showPage()
    pdf.save()
    return buffer.getvalue()


def test_extract_room_schedule_falls_back_to_claude_vision(
    db_session,
    tmp_path,
    monkeypatch,
):
    raw_dir = tmp_path / "data" / "raw"
    raw_dir.mkdir(parents=True)
    pdf_path = raw_dir / "rooms.pdf"
    pdf_path.write_bytes(_make_test_pdf())

    monkeypatch.setattr("app.parsing.raw_extract.get_repo_root", lambda: tmp_path)
    monkeypatch.setattr("app.parsing.room_schedule.get_repo_root", lambda: tmp_path)

    user = User(
        email="room-vision@example.com",
        hashed_password="hashed",
        created_at=datetime.now(UTC).replace(tzinfo=None),
    )
    db_session.add(user)
    db_session.flush()

    project = Project(name="Room Vision Project", owner_id=user.id)
    db_session.add(project)
    db_session.flush()

    drawing = Drawing(
        project_id=project.id,
        type=DrawingType.ARCHITECTURAL,
        file_path="data/raw/rooms.pdf",
        upload_date=datetime.now(UTC).replace(tzinfo=None),
    )
    db_session.add(drawing)
    db_session.commit()
    db_session.refresh(drawing)

    def fake_render(drawing_id_arg, page_number, db):
        output_dir = tmp_path / "data" / "processed" / str(drawing_id_arg)
        output_dir.mkdir(parents=True, exist_ok=True)
        image_path = output_dir / f"page_{page_number}.png"
        Image.new("RGB", (100, 100), color="white").save(image_path, "PNG")
        return f"data/processed/{drawing_id_arg}/page_{page_number}.png"

    def fake_claude(prompt, image_bytes=None):
        assert image_bytes is not None
        assert b"\x89PNG" in image_bytes[:8] or image_bytes.startswith(b"\x89PNG")
        assert "room" in prompt.lower()
        return json.dumps(
            {
                "rooms": [
                    {
                        "name": "Reception",
                        "occupancy_category": "Office - Reception",
                        "floor_area": 16.54,
                        "occupant_load": 0,
                    }
                ]
            }
        )

    monkeypatch.setattr(
        "app.parsing.room_schedule.extract_room_schedule_from_page",
        lambda page: [],
    )
    monkeypatch.setattr(
        "app.parsing.room_schedule.render_drawing_page",
        fake_render,
    )
    monkeypatch.setattr(
        "app.parsing.room_schedule.call_claude",
        fake_claude,
    )

    rows = extract_room_schedule(drawing.id, 1, db_session)

    assert rows == [
        {
            "name": "Reception",
            "occupancy_category": "Office - Reception",
            "floor_area": 16.54,
            "occupant_load": 0,
        }
    ]


def test_extract_room_schedule_skips_vision_when_pdfplumber_succeeds(
    db_session,
    tmp_path,
    monkeypatch,
):
    raw_dir = tmp_path / "data" / "raw"
    raw_dir.mkdir(parents=True)
    pdf_path = raw_dir / "rooms.pdf"
    pdf_path.write_bytes(_make_test_pdf())

    monkeypatch.setattr("app.parsing.raw_extract.get_repo_root", lambda: tmp_path)

    user = User(
        email="room-pdfplumber@example.com",
        hashed_password="hashed",
        created_at=datetime.now(UTC).replace(tzinfo=None),
    )
    db_session.add(user)
    db_session.flush()
    project = Project(name="Room Pdfplumber Project", owner_id=user.id)
    db_session.add(project)
    db_session.flush()
    drawing = Drawing(
        project_id=project.id,
        type=DrawingType.ARCHITECTURAL,
        file_path="data/raw/rooms.pdf",
        upload_date=datetime.now(UTC).replace(tzinfo=None),
    )
    db_session.add(drawing)
    db_session.commit()
    db_session.refresh(drawing)

    expected = [
        {
            "name": "Reception",
            "occupancy_category": "B",
            "floor_area": 42.5,
            "occupant_load": 5,
        }
    ]

    def fail_if_called(*args, **kwargs):
        raise AssertionError("Vision fallback should not run when pdfplumber succeeds")

    monkeypatch.setattr(
        "app.parsing.room_schedule.extract_room_schedule_from_page",
        lambda page: expected,
    )
    monkeypatch.setattr(
        "app.parsing.room_schedule._extract_room_schedule_via_vision",
        fail_if_called,
    )

    rows = extract_room_schedule(drawing.id, 1, db_session)
    assert rows == expected
