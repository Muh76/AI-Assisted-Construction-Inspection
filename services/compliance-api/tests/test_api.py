from tests.conftest import register_and_login


def test_create_project_and_room(client, auth_headers):
    project_response = client.post(
        "/api/v1/projects",
        json={"name": "Office Tower"},
        headers=auth_headers,
    )
    assert project_response.status_code == 201
    project_body = project_response.json()
    project_id = project_body["id"]
    assert project_body["owner_id"] > 0

    room_response = client.post(
        "/api/v1/rooms",
        json={
            "project_id": project_id,
            "name": "Lobby",
            "occupancy_category": "B",
            "floor_area": 500.0,
            "occupant_load": 50,
        },
        headers=auth_headers,
    )
    assert room_response.status_code == 201

    get_project_response = client.get(
        f"/api/v1/projects/{project_id}",
        headers=auth_headers,
    )
    assert get_project_response.status_code == 200
    assert get_project_response.json()["name"] == "Office Tower"

    get_room_response = client.get(
        f"/api/v1/rooms/{room_response.json()['id']}",
        headers=auth_headers,
    )
    assert get_room_response.status_code == 200
    assert get_room_response.json()["name"] == "Lobby"


def test_create_room_with_missing_project_returns_404(client, auth_headers):
    response = client.post(
        "/api/v1/rooms",
        json={
            "project_id": 99999,
            "name": "Lobby",
            "occupancy_category": "B",
            "floor_area": 500.0,
            "occupant_load": 50,
        },
        headers=auth_headers,
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Project not found"


def test_create_door_with_missing_room_returns_404(client, auth_headers):
    response = client.post(
        "/api/v1/doors",
        json={
            "room_id": 99999,
            "clear_width": 860.0,
            "fire_rating": "30 min",
        },
        headers=auth_headers,
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Room not found"


def test_project_compliance_endpoint(client, db_session, auth_headers):
    from app.models import RegulationClause

    db_session.add_all(
        [
            RegulationClause(
                code="OBC",
                section="3.3.2.4",
                title="Minimum corridor clear width",
                description="Corridor width threshold.",
                threshold_value=1100.0,
                threshold_unit="mm",
            ),
            RegulationClause(
                code="OBC",
                section="3.4.7.1",
                title="Minimum door clear width",
                description="Door width threshold.",
                threshold_value=860.0,
                threshold_unit="mm",
            ),
        ]
    )
    db_session.commit()

    project_id = client.post(
        "/api/v1/projects",
        json={"name": "Compliance Test Project"},
        headers=auth_headers,
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
        headers=auth_headers,
    ).json()["id"]

    client.post(
        "/api/v1/doors",
        json={"room_id": room_id, "clear_width": 860.0},
        headers=auth_headers,
    )
    client.post(
        "/api/v1/corridors",
        json={"project_id": project_id, "clear_width": 1100.0, "length": 12.0},
        headers=auth_headers,
    )

    response = client.get(
        f"/api/v1/projects/{project_id}/compliance",
        headers=auth_headers,
    )

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

    corridor_results = [
        result for result in report["results"] if result["rule_id"] == "corridor-min-width"
    ]
    door_results = [
        result for result in report["results"] if result["rule_id"] == "door-min-width"
    ]
    occupant_results = [
        result for result in report["results"] if result["rule_id"] == "occupant-load"
    ]

    assert corridor_results[0]["regulation_citation"] == "OBC 3.3.2.4"
    assert door_results[0]["regulation_citation"] == "OBC 3.4.7.1"
    assert occupant_results[0]["regulation_citation"] is None


def test_project_compliance_not_found(client, auth_headers):
    response = client.get(
        "/api/v1/projects/99999/compliance",
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_project_compliance_export_pdf(client, db_session, auth_headers):
    from app.models import RegulationClause

    db_session.add(
        RegulationClause(
            code="OBC",
            section="3.4.7.1",
            title="Minimum door clear width",
            description="Door width threshold.",
            threshold_value=860.0,
            threshold_unit="mm",
        )
    )
    db_session.commit()

    project_id = client.post(
        "/api/v1/projects",
        json={"name": "PDF Export Project"},
        headers=auth_headers,
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
        headers=auth_headers,
    ).json()["id"]

    client.post(
        "/api/v1/doors",
        json={"room_id": room_id, "clear_width": 860.0},
        headers=auth_headers,
    )

    response = client.get(
        f"/api/v1/projects/{project_id}/compliance/export",
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")
    assert "attachment" in response.headers["content-disposition"]
    assert f"compliance-report-project-{project_id}.pdf" in response.headers["content-disposition"]


def test_project_compliance_export_not_found(client, auth_headers):
    response = client.get(
        "/api/v1/projects/99999/compliance/export",
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_upload_drawing(client, tmp_path, monkeypatch, auth_headers):
    monkeypatch.setattr("app.routers.projects.get_data_raw_dir", lambda: tmp_path)

    project_id = client.post(
        "/api/v1/projects",
        json={"name": "Drawing Upload Project"},
        headers=auth_headers,
    ).json()["id"]

    pdf_content = b"%PDF-1.4 test drawing"
    response = client.post(
        f"/api/v1/projects/{project_id}/drawings",
        files={"file": ("floor-plan.pdf", pdf_content, "application/pdf")},
        data={"type": "architectural"},
        headers=auth_headers,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["project_id"] == project_id
    assert body["type"] == "architectural"
    assert body["file_path"].startswith("data/raw/project-")
    assert body["file_path"].endswith(".pdf")

    saved_files = list(tmp_path.glob("project-*.pdf"))
    assert len(saved_files) == 1
    assert saved_files[0].read_bytes() == pdf_content


def test_upload_drawing_project_not_found(client, tmp_path, monkeypatch, auth_headers):
    monkeypatch.setattr("app.routers.projects.get_data_raw_dir", lambda: tmp_path)

    response = client.post(
        "/api/v1/projects/99999/drawings",
        files={"file": ("floor-plan.pdf", b"%PDF-1.4", "application/pdf")},
        data={"type": "architectural"},
        headers=auth_headers,
    )

    assert response.status_code == 404


def test_protected_route_requires_auth(client):
    response = client.get("/api/v1/projects")
    assert response.status_code == 401


def test_user_cannot_access_other_users_project(client):
    headers_a = register_and_login(client, "user-a@example.com", "password-a")
    headers_b = register_and_login(client, "user-b@example.com", "password-b")

    project_b_id = client.post(
        "/api/v1/projects",
        json={"name": "User B Project"},
        headers=headers_b,
    ).json()["id"]

    response = client.get(f"/api/v1/projects/{project_b_id}", headers=headers_a)
    assert response.status_code == 404
    assert response.json()["detail"] == "Project not found"
