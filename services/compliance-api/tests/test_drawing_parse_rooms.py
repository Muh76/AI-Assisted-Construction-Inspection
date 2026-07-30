from unittest.mock import patch

import pytest
from sqlalchemy import select

from app.models import Room


@pytest.fixture
def sample_parsed_room_rows() -> list[dict]:
    return [
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
    ]


def test_preview_parsed_rooms(client, sample_parsed_room_rows, auth_headers):
    project_id = client.post(
        "/api/v1/projects",
        json={"name": "Room Parse Preview Project"},
        headers=auth_headers,
    ).json()["id"]

    drawing_id = 42
    with patch(
        "app.routers.drawings.extract_room_schedule",
        return_value=sample_parsed_room_rows,
    ):
        with patch("app.routers.drawings._get_drawing_or_404") as mock_get_drawing:
            from types import SimpleNamespace

            mock_get_drawing.return_value = SimpleNamespace(
                id=drawing_id,
                project_id=project_id,
            )
            response = client.post(
                f"/api/v1/drawings/{drawing_id}/parse-rooms?page_number=2"
            )

    assert response.status_code == 200
    body = response.json()
    assert body == {
        "drawing_id": drawing_id,
        "page_number": 2,
        "preview": True,
        "rows": sample_parsed_room_rows,
    }


def test_preview_parsed_rooms_drawing_not_found(client):
    response = client.post("/api/v1/drawings/99999/parse-rooms")
    assert response.status_code == 404
    assert response.json()["detail"] == "Drawing not found"


def test_confirm_parsed_rooms(client, db_session, sample_parsed_room_rows, auth_headers):
    project_id = client.post(
        "/api/v1/projects",
        json={"name": "Room Parse Confirm Project"},
        headers=auth_headers,
    ).json()["id"]

    from datetime import UTC, datetime

    from app.models import Drawing, DrawingType

    drawing = Drawing(
        project_id=project_id,
        type=DrawingType.ARCHITECTURAL,
        file_path="data/raw/test.pdf",
        upload_date=datetime.now(UTC).replace(tzinfo=None),
    )
    db_session.add(drawing)
    db_session.commit()

    confirm_rows = [
        {
            **sample_parsed_room_rows[0],
            "floor_area": 45.0,
        },
        sample_parsed_room_rows[1],
    ]

    response = client.post(
        f"/api/v1/drawings/{drawing.id}/parse-rooms/confirm",
        json={"rows": confirm_rows},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["drawing_id"] == drawing.id
    assert len(body["created"]) == 2
    assert body["created"][0]["project_id"] == project_id
    assert body["created"][0]["name"] == "Reception"
    assert body["created"][0]["floor_area"] == 45.0
    assert body["created"][0]["occupant_load"] == 5
    assert body["created"][1]["name"] == "Office 101"

    rooms = list(db_session.scalars(select(Room)).all())
    assert len(rooms) == 2
