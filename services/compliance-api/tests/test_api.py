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
