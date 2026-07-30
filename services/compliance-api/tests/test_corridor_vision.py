import json
from datetime import UTC, datetime
from io import BytesIO

from PIL import Image
from reportlab.pdfgen import canvas

from app.models import Drawing, DrawingType
from app.parsing.corridor_vision import _parse_llm_response


def test_parse_llm_response_normalizes_callouts():
    content = json.dumps(
        {
            "callouts": [
                {
                    "label": "Corridor A",
                    "width_mm": 1100,
                    "approximate_location": "upper center",
                },
                {
                    "label": "",
                    "width_mm": 900,
                    "approximate_location": "lower left",
                },
                {
                    "label": "Corridor B",
                    "width_mm": "not-a-number",
                    "approximate_location": "right side",
                },
            ]
        }
    )

    callouts = _parse_llm_response(content)

    assert callouts == [
        {
            "label": "Corridor A",
            "width_mm": 1100.0,
            "approximate_location": "upper center",
        }
    ]


def _make_test_pdf() -> bytes:
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer)
    pdf.drawString(72, 720, "Corridor plan")
    pdf.showPage()
    pdf.save()
    return buffer.getvalue()


def _configure_paths(monkeypatch, tmp_path):
    raw_dir = tmp_path / "data" / "raw"
    raw_dir.mkdir(parents=True)
    monkeypatch.setattr("app.routers.projects.get_data_raw_dir", lambda: raw_dir)
    monkeypatch.setattr("app.parsing.raw_extract.get_repo_root", lambda: tmp_path)
    monkeypatch.setattr("app.parsing.page_image.get_repo_root", lambda: tmp_path)
    monkeypatch.setattr("app.parsing.corridor_vision.get_repo_root", lambda: tmp_path)
    return raw_dir


def test_preview_parsed_corridor_widths(client, tmp_path, monkeypatch, auth_headers):
    _configure_paths(monkeypatch, tmp_path)
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")

    project_id = client.post(
        "/api/v1/projects",
        json={"name": "Corridor Vision Project"},
        headers=auth_headers,
    ).json()["id"]

    upload_response = client.post(
        f"/api/v1/projects/{project_id}/drawings",
        files={"file": ("floor-plan.pdf", _make_test_pdf(), "application/pdf")},
        data={"type": "architectural"},
        headers=auth_headers,
    )
    drawing_id = upload_response.json()["id"]

    def fake_render(drawing_id_arg, page_number, db):
        output_dir = tmp_path / "data" / "processed" / str(drawing_id_arg)
        output_dir.mkdir(parents=True, exist_ok=True)
        image_path = output_dir / f"page_{page_number}.png"
        Image.new("RGB", (100, 100), color="white").save(image_path, "PNG")
        return f"data/processed/{drawing_id_arg}/page_{page_number}.png"

    def fake_request(image_path):
        assert image_path.is_file()
        return [
            {
                "label": "Main corridor",
                "width_mm": 1200.0,
                "approximate_location": "center of page",
            }
        ]

    monkeypatch.setattr(
        "app.parsing.corridor_vision.render_drawing_page",
        fake_render,
    )
    monkeypatch.setattr(
        "app.parsing.corridor_vision._request_corridor_callouts",
        fake_request,
    )

    response = client.post(
        f"/api/v1/drawings/{drawing_id}/pages/1/parse-corridors",
        headers=auth_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["drawing_id"] == drawing_id
    assert body["page_number"] == 1
    assert body["preview"] is True
    assert body["image_path"] == f"data/processed/{drawing_id}/page_1.png"
    assert body["callouts"] == [
        {
            "label": "Main corridor",
            "width_mm": 1200.0,
            "approximate_location": "center of page",
        }
    ]


def test_preview_parsed_corridor_widths_missing_api_key(
    client,
    db_session,
    monkeypatch,
    auth_headers,
):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(
        "app.parsing.corridor_vision.render_drawing_page",
        lambda drawing_id, page_number, db: f"data/processed/{drawing_id}/page_{page_number}.png",
    )

    def raise_missing_key(_image_path):
        raise RuntimeError("OPENAI_API_KEY environment variable is not set")

    monkeypatch.setattr(
        "app.parsing.corridor_vision._request_corridor_callouts",
        raise_missing_key,
    )

    project_id = client.post(
        "/api/v1/projects",
        json={"name": "Corridor Vision Missing Key Project"},
        headers=auth_headers,
    ).json()["id"]

    drawing = Drawing(
        project_id=project_id,
        type=DrawingType.ARCHITECTURAL,
        file_path="data/raw/floor-plan.pdf",
        upload_date=datetime.now(UTC).replace(tzinfo=None),
    )
    db_session.add(drawing)
    db_session.commit()

    response = client.post(
        f"/api/v1/drawings/{drawing.id}/pages/1/parse-corridors",
        headers=auth_headers,
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "OPENAI_API_KEY environment variable is not set"


def test_confirm_parsed_corridor_widths(client, tmp_path, monkeypatch, auth_headers):
    _configure_paths(monkeypatch, tmp_path)
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")

    project_id = client.post(
        "/api/v1/projects",
        json={"name": "Corridor Vision Confirm Project"},
        headers=auth_headers,
    ).json()["id"]

    upload_response = client.post(
        f"/api/v1/projects/{project_id}/drawings",
        files={"file": ("floor-plan.pdf", _make_test_pdf(), "application/pdf")},
        data={"type": "architectural"},
        headers=auth_headers,
    )
    drawing_id = upload_response.json()["id"]

    response = client.post(
        f"/api/v1/drawings/{drawing_id}/pages/1/parse-corridors/confirm",
        json={
            "callouts": [
                {
                    "label": "Main corridor",
                    "width_mm": 1200.0,
                    "approximate_location": "center of page",
                    "length": 18.5,
                }
            ]
        },
        headers=auth_headers,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["drawing_id"] == drawing_id
    assert body["page_number"] == 1
    assert len(body["created"]) == 1
    assert body["created"][0]["project_id"] == project_id
    assert body["created"][0]["clear_width"] == 1200.0
    assert body["created"][0]["length"] == 18.5
