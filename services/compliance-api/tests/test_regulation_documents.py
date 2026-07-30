def test_upload_regulation_document(client, tmp_path, monkeypatch, auth_headers):
    monkeypatch.setattr(
        "app.routers.regulations.get_data_regulations_dir",
        lambda: tmp_path,
    )

    pdf_content = b"%PDF-1.4 test regulation"
    response = client.post(
        "/api/v1/regulations/documents",
        files={"file": ("obc-2024.pdf", pdf_content, "application/pdf")},
        data={"code": "OBC", "edition": "2024"},
        headers=auth_headers,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["code"] == "OBC"
    assert body["edition"] == "2024"
    assert body["file_path"].startswith("data/regulations/OBC-2024-")
    assert body["file_path"].endswith(".pdf")
    assert body["uploaded_at"] is not None

    saved_files = list(tmp_path.glob("OBC-2024-*.pdf"))
    assert len(saved_files) == 1
    assert saved_files[0].read_bytes() == pdf_content


def test_upload_regulation_document_rejects_non_pdf(client, tmp_path, monkeypatch, auth_headers):
    monkeypatch.setattr(
        "app.routers.regulations.get_data_regulations_dir",
        lambda: tmp_path,
    )

    response = client.post(
        "/api/v1/regulations/documents",
        files={"file": ("notes.txt", b"not a pdf", "text/plain")},
        data={"code": "OBC", "edition": "2024"},
        headers=auth_headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Only PDF files are allowed"


def test_upload_regulation_document_requires_auth(client, tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.routers.regulations.get_data_regulations_dir",
        lambda: tmp_path,
    )

    response = client.post(
        "/api/v1/regulations/documents",
        files={"file": ("obc-2024.pdf", b"%PDF-1.4", "application/pdf")},
        data={"code": "OBC", "edition": "2024"},
    )

    assert response.status_code == 401
