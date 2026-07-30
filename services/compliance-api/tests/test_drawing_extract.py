from io import BytesIO

from reportlab.pdfgen import canvas
from sqlalchemy import select

from app.models import DrawingText


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
    return raw_dir


def test_extract_drawing_text(client, db_session, tmp_path, monkeypatch, auth_headers):
    raw_dir = _configure_drawing_paths(monkeypatch, tmp_path)

    project_id = client.post(
        "/api/v1/projects",
        json={"name": "Drawing Extract Project"},
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

    extract_response = client.post(f"/api/v1/drawings/{drawing_id}/extract")

    assert extract_response.status_code == 200
    body = extract_response.json()
    assert body == {"drawing_id": drawing_id, "pages_processed": 2}

    pages = list(
        db_session.scalars(
            select(DrawingText)
            .where(DrawingText.drawing_id == drawing_id)
            .order_by(DrawingText.page_number)
        ).all()
    )
    assert len(pages) == 2
    assert pages[0].page_number == 1
    assert pages[1].page_number == 2
    assert "Page one text" in pages[0].raw_text
    assert "Page two text" in pages[1].raw_text
    assert list(raw_dir.glob("project-*.pdf"))


def test_extract_drawing_text_not_found(client):
    response = client.post("/api/v1/drawings/99999/extract")
    assert response.status_code == 404
    assert response.json()["detail"] == "Drawing not found"


def test_extract_drawing_text_missing_pdf(client, db_session, tmp_path, monkeypatch, auth_headers):
    _configure_drawing_paths(monkeypatch, tmp_path)

    from datetime import UTC, datetime

    from app.models import Drawing, DrawingType

    project_id = client.post(
        "/api/v1/projects",
        json={"name": "Missing PDF Project"},
        headers=auth_headers,
    ).json()["id"]

    drawing = Drawing(
        project_id=project_id,
        type=DrawingType.ARCHITECTURAL,
        file_path="data/raw/missing.pdf",
        upload_date=datetime.now(UTC).replace(tzinfo=None),
    )
    db_session.add(drawing)
    db_session.commit()

    response = client.post(f"/api/v1/drawings/{drawing.id}/extract")
    assert response.status_code == 404
    assert "Drawing PDF not found" in response.json()["detail"]
