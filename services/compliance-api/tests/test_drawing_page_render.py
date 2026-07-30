from io import BytesIO
from unittest.mock import patch

from PIL import Image
from reportlab.pdfgen import canvas


def _make_test_pdf(page_texts: list[str]) -> bytes:
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer)
    for text in page_texts:
        pdf.drawString(72, 720, text)
        pdf.showPage()
    pdf.save()
    return buffer.getvalue()


def _configure_drawing_paths(monkeypatch, tmp_path):
    raw_dir = tmp_path / "data" / "raw"
    raw_dir.mkdir(parents=True)
    monkeypatch.setattr("app.routers.projects.get_data_raw_dir", lambda: raw_dir)
    monkeypatch.setattr("app.parsing.raw_extract.get_repo_root", lambda: tmp_path)
    monkeypatch.setattr("app.parsing.page_image.get_repo_root", lambda: tmp_path)
    return raw_dir


def _fake_convert_from_path(*_args, **_kwargs):
    return [Image.new("RGB", (120, 80), color="white")]


def test_render_drawing_page(client, tmp_path, monkeypatch, auth_headers):
    _configure_drawing_paths(monkeypatch, tmp_path)

    project_id = client.post(
        "/api/v1/projects",
        json={"name": "Drawing Render Project"},
        headers=auth_headers,
    ).json()["id"]

    pdf_bytes = _make_test_pdf(["Page one text", "Page two text"])
    upload_response = client.post(
        f"/api/v1/projects/{project_id}/drawings",
        files={"file": ("floor-plan.pdf", pdf_bytes, "application/pdf")},
        data={"type": "architectural"},
        headers=auth_headers,
    )
    assert upload_response.status_code == 201
    drawing_id = upload_response.json()["id"]

    with patch(
        "app.parsing.page_image.convert_from_path",
        side_effect=_fake_convert_from_path,
    ):
        response = client.post(
            f"/api/v1/drawings/{drawing_id}/pages/2/render",
            headers=auth_headers,
        )

    assert response.status_code == 200
    body = response.json()
    assert body == {
        "drawing_id": drawing_id,
        "page_number": 2,
        "file_path": f"data/processed/{drawing_id}/page_2.png",
    }

    saved_path = tmp_path / body["file_path"]
    assert saved_path.is_file()
    assert saved_path.stat().st_size > 0


def test_render_drawing_page_not_found(client, auth_headers):
    response = client.post(
        "/api/v1/drawings/99999/pages/1/render",
        headers=auth_headers,
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Drawing not found"


def test_render_drawing_page_invalid_page_number(client, tmp_path, monkeypatch, auth_headers):
    _configure_drawing_paths(monkeypatch, tmp_path)

    project_id = client.post(
        "/api/v1/projects",
        json={"name": "Drawing Render Invalid Page Project"},
        headers=auth_headers,
    ).json()["id"]

    pdf_bytes = _make_test_pdf(["Page one text"])
    upload_response = client.post(
        f"/api/v1/projects/{project_id}/drawings",
        files={"file": ("floor-plan.pdf", pdf_bytes, "application/pdf")},
        data={"type": "architectural"},
        headers=auth_headers,
    )
    drawing_id = upload_response.json()["id"]

    response = client.post(
        f"/api/v1/drawings/{drawing_id}/pages/5/render",
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert "exceeds drawing page count" in response.json()["detail"]
