from unittest.mock import patch

import pytest
from sqlalchemy import select

from app.models import Door


@pytest.fixture
def sample_parsed_door_rows() -> list[dict]:
    return [
        {"door_number": "D-101", "width": 860.0, "fire_rating": "30 min"},
        {"door_number": "D-102", "width": 920.0, "fire_rating": "45 min"},
    ]


def test_preview_parsed_doors(client, sample_parsed_door_rows):
    project_id = client.post(
        "/api/v1/projects",
        json={"name": "Door Parse Preview Project"},
    ).json()["id"]

    drawing_id = 42
    with patch(
        "app.routers.drawings.extract_door_schedule",
        return_value=sample_parsed_door_rows,
    ):
        with patch("app.routers.drawings._get_drawing_or_404") as mock_get_drawing:
            from types import SimpleNamespace

            mock_get_drawing.return_value = SimpleNamespace(
                id=drawing_id,
                project_id=project_id,
            )
            response = client.post(
                f"/api/v1/drawings/{drawing_id}/parse-doors?page_number=2"
            )

    assert response.status_code == 200
    body = response.json()
    assert body == {
        "drawing_id": drawing_id,
        "page_number": 2,
        "preview": True,
        "rows": sample_parsed_door_rows,
    }


def test_preview_parsed_doors_drawing_not_found(client):
    response = client.post("/api/v1/drawings/99999/parse-doors")
    assert response.status_code == 404
    assert response.json()["detail"] == "Drawing not found"


def test_confirm_parsed_doors(client, db_session, sample_parsed_door_rows):
    project_id = client.post(
        "/api/v1/projects",
        json={"name": "Door Parse Confirm Project"},
    ).json()["id"]

    room_a_id = client.post(
        "/api/v1/rooms",
        json={
            "project_id": project_id,
            "name": "Office A",
            "occupancy_category": "office",
            "floor_area": 18.6,
            "occupant_load": 2,
        },
    ).json()["id"]

    room_b_id = client.post(
        "/api/v1/rooms",
        json={
            "project_id": project_id,
            "name": "Office B",
            "occupancy_category": "office",
            "floor_area": 20.0,
            "occupant_load": 2,
        },
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
            **sample_parsed_door_rows[0],
            "room_id": room_a_id,
            "width": 870.0,
        },
        {
            **sample_parsed_door_rows[1],
            "room_id": room_b_id,
            "fire_rating": "60 min",
        },
    ]

    response = client.post(
        f"/api/v1/drawings/{drawing.id}/parse-doors/confirm",
        json={"rows": confirm_rows},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["drawing_id"] == drawing.id
    assert len(body["created"]) == 2
    assert body["created"][0]["room_id"] == room_a_id
    assert body["created"][0]["clear_width"] == 870.0
    assert body["created"][0]["fire_rating"] == "30 min"
    assert body["created"][1]["room_id"] == room_b_id
    assert body["created"][1]["clear_width"] == 920.0
    assert body["created"][1]["fire_rating"] == "60 min"

    doors = list(db_session.scalars(select(Door)).all())
    assert len(doors) == 2


def test_confirm_parsed_doors_room_not_found(client, db_session):
    project_id = client.post(
        "/api/v1/projects",
        json={"name": "Door Confirm Missing Room"},
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

    response = client.post(
        f"/api/v1/drawings/{drawing.id}/parse-doors/confirm",
        json={
            "rows": [
                {
                    "door_number": "D-101",
                    "width": 860.0,
                    "fire_rating": "30 min",
                    "room_id": 99999,
                }
            ]
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Room 99999 not found"


def test_confirm_parsed_doors_room_wrong_project(client, db_session):
    project_a_id = client.post(
        "/api/v1/projects",
        json={"name": "Project A"},
    ).json()["id"]
    project_b_id = client.post(
        "/api/v1/projects",
        json={"name": "Project B"},
    ).json()["id"]

    room_id = client.post(
        "/api/v1/rooms",
        json={
            "project_id": project_b_id,
            "name": "Office",
            "occupancy_category": "office",
            "floor_area": 18.6,
            "occupant_load": 2,
        },
    ).json()["id"]

    from datetime import UTC, datetime

    from app.models import Drawing, DrawingType

    drawing = Drawing(
        project_id=project_a_id,
        type=DrawingType.ARCHITECTURAL,
        file_path="data/raw/test.pdf",
        upload_date=datetime.now(UTC).replace(tzinfo=None),
    )
    db_session.add(drawing)
    db_session.commit()

    response = client.post(
        f"/api/v1/drawings/{drawing.id}/parse-doors/confirm",
        json={
            "rows": [
                {
                    "door_number": "D-101",
                    "width": 860.0,
                    "fire_rating": "30 min",
                    "room_id": room_id,
                }
            ]
        },
    )

    assert response.status_code == 400
    assert "does not belong to the same project" in response.json()["detail"]
