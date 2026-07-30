def test_create_project_and_room(client):
    project_response = client.post(
        "/api/v1/projects",
        json={"name": "Office Tower"},
    )
    assert project_response.status_code == 201
    project_id = project_response.json()["id"]

    room_response = client.post(
        "/api/v1/rooms",
        json={
            "project_id": project_id,
            "name": "Lobby",
            "occupancy_category": "B",
            "floor_area": 500.0,
            "occupant_load": 50,
        },
    )
    assert room_response.status_code == 201

    get_project_response = client.get(f"/api/v1/projects/{project_id}")
    assert get_project_response.status_code == 200
    assert get_project_response.json()["name"] == "Office Tower"

    get_room_response = client.get(f"/api/v1/rooms/{room_response.json()['id']}")
    assert get_room_response.status_code == 200
    assert get_room_response.json()["name"] == "Lobby"


def test_create_room_with_missing_project_returns_404(client):
    response = client.post(
        "/api/v1/rooms",
        json={
            "project_id": 99999,
            "name": "Lobby",
            "occupancy_category": "B",
            "floor_area": 500.0,
            "occupant_load": 50,
        },
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Project not found"


def test_create_door_with_missing_room_returns_404(client):
    response = client.post(
        "/api/v1/doors",
        json={
            "room_id": 99999,
            "clear_width": 860.0,
            "fire_rating": "30 min",
        },
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Room not found"


def test_project_compliance_endpoint(client):
    project_id = client.post(
        "/api/v1/projects",
        json={"name": "Compliance Test Project"},
    ).json()["id"]

    room_id = client.post(
        "/api/v1/rooms",
        json={
            "project_id": project_id,
            "name": "Office",
            "occupancy_category": "office",
            "floor_area": 18.6,
            "occupant_load": 2,
        },
    ).json()["id"]

    client.post(
        "/api/v1/doors",
        json={"room_id": room_id, "clear_width": 860.0},
    )
    client.post(
        "/api/v1/corridors",
        json={"project_id": project_id, "clear_width": 1100.0, "length": 12.0},
    )

    response = client.get(f"/api/v1/projects/{project_id}/compliance")

    assert response.status_code == 200
    report = response.json()
    assert report["project_id"] == project_id
    assert "generated_at" in report
    assert isinstance(report["results"], list)
    assert len(report["results"]) >= 3
    assert report["summary"]["passed"] + report["summary"]["failed"] == len(report["results"])

    rule_ids = {result["rule_id"] for result in report["results"]}
    assert "corridor-min-width" in rule_ids
    assert "door-min-width" in rule_ids
    assert "occupant-load" in rule_ids


def test_project_compliance_not_found(client):
    response = client.get("/api/v1/projects/99999/compliance")
    assert response.status_code == 404


def test_project_compliance_export_pdf(client):
    project_id = client.post(
        "/api/v1/projects",
        json={"name": "PDF Export Project"},
    ).json()["id"]

    room_id = client.post(
        "/api/v1/rooms",
        json={
            "project_id": project_id,
            "name": "Office",
            "occupancy_category": "office",
            "floor_area": 18.6,
            "occupant_load": 2,
        },
    ).json()["id"]

    client.post(
        "/api/v1/doors",
        json={"room_id": room_id, "clear_width": 860.0},
    )

    response = client.get(f"/api/v1/projects/{project_id}/compliance/export")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")
    assert "attachment" in response.headers["content-disposition"]
    assert f"compliance-report-project-{project_id}.pdf" in response.headers["content-disposition"]


def test_project_compliance_export_not_found(client):
    response = client.get("/api/v1/projects/99999/compliance/export")
    assert response.status_code == 404
