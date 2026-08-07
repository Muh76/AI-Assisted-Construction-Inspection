import json
from datetime import UTC, datetime
from io import BytesIO
from unittest.mock import patch

import pytest
from reportlab.pdfgen import canvas
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.models import User
from scripts.validate_extraction import (
    compare_against_ground_truth,
    print_accuracy_report,
    validate_extraction,
)


def _make_test_pdf() -> bytes:
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer)
    pdf.drawString(72, 720, "Door schedule")
    pdf.showPage()
    pdf.save()
    return buffer.getvalue()


@pytest.fixture
def validation_db_session(tmp_path, monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(autocommit=False, autoflush=False, bind=engine)()

    raw_dir = tmp_path / "data" / "raw"
    raw_dir.mkdir(parents=True)
    monkeypatch.setattr("scripts.validate_extraction.get_data_raw_dir", lambda: raw_dir)
    monkeypatch.setattr("scripts.validate_extraction.get_repo_root", lambda: tmp_path)

    user = User(
        email="validate-extraction@example.com",
        hashed_password="hashed",
        created_at=datetime.now(UTC).replace(tzinfo=None),
    )
    session.add(user)
    session.commit()

    monkeypatch.setattr(
        "scripts.validate_extraction._get_or_create_seed_user",
        lambda db: user,
    )
    monkeypatch.setattr(
        "scripts.validate_extraction.SessionLocal",
        lambda: session,
    )

    pdf_path = tmp_path / "interior_design.pdf"
    pdf_path.write_bytes(_make_test_pdf())

    try:
        yield session, pdf_path
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def test_validate_extraction_prints_json(validation_db_session):
    _session, pdf_path = validation_db_session

    with patch(
        "scripts.validate_extraction.extract_door_schedule",
        return_value=[{"door_number": "D-1", "width": 860.0, "fire_rating": None}],
    ), patch(
        "scripts.validate_extraction.extract_room_schedule",
        return_value=[
            {
                "name": "Office",
                "occupancy_category": "B",
                "floor_area": 20.0,
                "occupant_load": 2,
            }
        ],
    ), patch(
        "scripts.validate_extraction._count_pdf_pages",
        return_value=10,
    ):
        result = validate_extraction(pdf_path=pdf_path, door_page=2, room_page=3)

    assert result["page_count"] == 10
    assert result["door_page"] == 2
    assert result["room_page"] == 3
    assert result["doors_source_pdf"] == str(pdf_path)
    assert result["rooms_source_pdf"] == str(pdf_path)
    assert len(result["doors"]) == 1
    assert len(result["rooms"]) == 1

    dumped = json.dumps(result)
    parsed = json.loads(dumped)
    assert parsed["doors"][0]["door_number"] == "D-1"


def test_validate_extraction_uses_separate_doors_and_rooms_pdfs(validation_db_session):
    _session, doors_pdf = validation_db_session
    rooms_pdf = doors_pdf.parent / "rooms.pdf"
    rooms_pdf.write_bytes(_make_test_pdf())

    with patch(
        "scripts.validate_extraction.extract_door_schedule",
        return_value=[{"door_number": "D-1", "width": 860.0, "fire_rating": None}],
    ) as door_extract, patch(
        "scripts.validate_extraction.extract_room_schedule",
        return_value=[
            {
                "name": "Office",
                "occupancy_category": "B",
                "floor_area": 20.0,
                "occupant_load": 2,
            }
        ],
    ) as room_extract, patch(
        "scripts.validate_extraction._count_pdf_pages",
        return_value=4,
    ):
        result = validate_extraction(
            doors_pdf=doors_pdf,
            rooms_pdf=rooms_pdf,
            door_page=1,
            room_page=2,
        )

    assert result["doors_source_pdf"] == str(doors_pdf)
    assert result["rooms_source_pdf"] == str(rooms_pdf)
    assert result["doors_drawing_id"] != result["rooms_drawing_id"]
    assert "source_pdf" not in result
    door_extract.assert_called_once()
    room_extract.assert_called_once()
    assert door_extract.call_args.args[0] == result["doors_drawing_id"]
    assert room_extract.call_args.args[0] == result["rooms_drawing_id"]
    assert door_extract.call_args.args[1] == 1
    assert room_extract.call_args.args[1] == 2


def test_compare_against_ground_truth_counts():
    ground_truth = {
        "doors": [
            {
                "door_no": "D-101",
                "clear_width_mm": 860,
                "fire_rating": "30 min",
            },
            {
                "door_no": "D-102",
                "clear_width_mm": 920,
                "fire_rating": "",
            },
            {
                "door_no": "D-103",
                "clear_width_mm": 900,
                "fire_rating": None,
            },
        ],
        "rooms": [
            {
                "room_no": "101",
                "name": "Reception",
                "occupancy_category": "B",
                "floor_area": 42.0,
                "occupant_load": 14,
            },
            {
                "room_no": "102",
                "name": "Office",
                "occupancy_category": "B",
                "floor_area": 12.5,
                "occupant_load": 2,
            },
        ],
    }
    extracted_doors = [
        {
            "door_number": "D-101",
            "width": 860.0,
            "fire_rating": "30 min",
        },
        {
            "door_number": "D-102",
            "width": 800.0,
            "fire_rating": None,
        },
    ]
    extracted_rooms = [
        {
            "name": "Reception",
            "occupancy_category": "B",
            "floor_area": 42.0,
            "occupant_load": 14,
        },
    ]

    report = compare_against_ground_truth(
        ground_truth,
        extracted_doors,
        extracted_rooms,
    )

    assert report.doors.matched_exactly == 1
    assert report.doors.field_wrong == 1
    assert report.doors.missed_entirely == 1
    assert report.rooms.matched_exactly == 1
    assert report.rooms.missed_entirely == 1
    assert report.rooms.field_wrong == 0


def test_compare_against_ground_truth_skips_placeholder_rows():
    ground_truth = {
        "doors": [{"door_no": "", "clear_width_mm": None, "fire_rating": ""}],
        "rooms": [
            {
                "room_no": "",
                "name": "",
                "occupancy_category": "",
                "floor_area": None,
                "occupant_load": None,
            }
        ],
    }

    report = compare_against_ground_truth(ground_truth, [], [])

    assert report.doors.matched_exactly == 0
    assert report.doors.missed_entirely == 0
    assert report.doors.field_wrong == 0
    assert report.rooms.matched_exactly == 0
    assert report.rooms.missed_entirely == 0
    assert report.rooms.field_wrong == 0


def test_print_accuracy_report(capsys):
    from scripts.validate_extraction import AccuracyReport, CategoryAccuracyReport

    print_accuracy_report(
        AccuracyReport(
            doors=CategoryAccuracyReport(
                matched_exactly=2,
                missed_entirely=1,
                field_wrong=3,
            ),
            rooms=CategoryAccuracyReport(
                matched_exactly=4,
                missed_entirely=0,
                field_wrong=1,
            ),
        )
    )

    output = capsys.readouterr().err
    assert "Doors" in output
    assert "matched exactly:   2" in output
    assert "missed entirely:   1" in output
    assert "field wrong:       3" in output
    assert "Rooms" in output
    assert "matched exactly:   4" in output

