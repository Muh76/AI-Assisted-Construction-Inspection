from io import BytesIO

from reportlab.pdfgen import canvas
from sqlalchemy import select

from app.models import RegulationText


def _make_test_pdf(page_texts: list[str]) -> bytes:
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer)
    for text in page_texts:
        pdf.drawString(72, 720, text)
        pdf.showPage()
    pdf.save()
    return buffer.getvalue()


def _configure_regulation_paths(monkeypatch, tmp_path):
    regulations_dir = tmp_path / "data" / "regulations"
    regulations_dir.mkdir(parents=True)
    monkeypatch.setattr(
        "app.routers.regulations.get_data_regulations_dir",
        lambda: regulations_dir,
    )
    monkeypatch.setattr("app.parsing.regulation_text.get_repo_root", lambda: tmp_path)
    return regulations_dir


def _upload_regulation_document(client, auth_headers, pdf_bytes, monkeypatch, tmp_path):
    _configure_regulation_paths(monkeypatch, tmp_path)
    response = client.post(
        "/api/v1/regulations/documents",
        files={"file": ("obc-2024.pdf", pdf_bytes, "application/pdf")},
        data={"code": "OBC", "edition": "2024"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_extract_regulation_pages(client, db_session, tmp_path, monkeypatch, auth_headers):
    pdf_bytes = _make_test_pdf(["Page one text", "Page two text", "Page three text"])
    document_id = _upload_regulation_document(
        client, auth_headers, pdf_bytes, monkeypatch, tmp_path
    )

    extract_response = client.post(
        f"/api/v1/regulations/documents/{document_id}/extract",
        params={"start": 2, "end": 3},
        headers=auth_headers,
    )

    assert extract_response.status_code == 200
    assert extract_response.json() == {
        "document_id": document_id,
        "start_page": 2,
        "end_page": 3,
        "pages_processed": 2,
    }

    pages = list(
        db_session.scalars(
            select(RegulationText)
            .where(RegulationText.document_id == document_id)
            .order_by(RegulationText.page_number)
        ).all()
    )
    assert len(pages) == 2
    assert pages[0].page_number == 2
    assert pages[1].page_number == 3
    assert "Page two text" in pages[0].raw_text
    assert "Page three text" in pages[1].raw_text


def test_extract_regulation_pages_replaces_existing_range(
    client, db_session, tmp_path, monkeypatch, auth_headers
):
    pdf_bytes = _make_test_pdf(["Page one text", "Page two text", "Page three text"])
    document_id = _upload_regulation_document(
        client, auth_headers, pdf_bytes, monkeypatch, tmp_path
    )

    first_response = client.post(
        f"/api/v1/regulations/documents/{document_id}/extract",
        params={"start": 1, "end": 3},
        headers=auth_headers,
    )
    assert first_response.status_code == 200

    second_response = client.post(
        f"/api/v1/regulations/documents/{document_id}/extract",
        params={"start": 2, "end": 2},
        headers=auth_headers,
    )
    assert second_response.status_code == 200

    pages = list(
        db_session.scalars(
            select(RegulationText)
            .where(RegulationText.document_id == document_id)
            .order_by(RegulationText.page_number)
        ).all()
    )
    assert [page.page_number for page in pages] == [1, 2, 3]


def test_extract_regulation_pages_not_found(client, auth_headers):
    response = client.post(
        "/api/v1/regulations/documents/99999/extract",
        params={"start": 1, "end": 1},
        headers=auth_headers,
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Regulation document not found"


def test_extract_regulation_pages_invalid_range(client, tmp_path, monkeypatch, auth_headers):
    pdf_bytes = _make_test_pdf(["Page one text"])
    document_id = _upload_regulation_document(
        client, auth_headers, pdf_bytes, monkeypatch, tmp_path
    )

    response = client.post(
        f"/api/v1/regulations/documents/{document_id}/extract",
        params={"start": 3, "end": 1},
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "end must be greater than or equal to start"


def test_extract_regulation_pages_beyond_document(client, tmp_path, monkeypatch, auth_headers):
    pdf_bytes = _make_test_pdf(["Page one text"])
    document_id = _upload_regulation_document(
        client, auth_headers, pdf_bytes, monkeypatch, tmp_path
    )

    response = client.post(
        f"/api/v1/regulations/documents/{document_id}/extract",
        params={"start": 1, "end": 5},
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert "exceeds document page count" in response.json()["detail"]


def test_extract_regulation_pages_missing_pdf(
    client, db_session, tmp_path, monkeypatch, auth_headers
):
    _configure_regulation_paths(monkeypatch, tmp_path)

    from datetime import UTC, datetime

    from app.models import RegulationDocument

    document = RegulationDocument(
        code="OBC",
        edition="2024",
        file_path="data/regulations/missing.pdf",
        uploaded_at=datetime.now(UTC).replace(tzinfo=None),
    )
    db_session.add(document)
    db_session.commit()

    response = client.post(
        f"/api/v1/regulations/documents/{document.id}/extract",
        params={"start": 1, "end": 1},
        headers=auth_headers,
    )
    assert response.status_code == 404
    assert "Regulation PDF not found" in response.json()["detail"]
